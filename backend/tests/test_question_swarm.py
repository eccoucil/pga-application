"""Tests for the question generation swarm."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.question_swarm import (
    QuestionGenerationSwarm,
    SwarmResult,
    WorkerAgent,
    _extract_json_array,
    _parse_questions,
)
from app.services.question_swarm_prompts import (
    build_controls_section,
    build_shared_context,
    format_batch_controls,
)


# ── Fixtures ─────────────────────────────────────────────────────────


def _make_controls(n: int) -> list[dict]:
    """Create n fake controls for testing."""
    return [
        {
            "id": f"A.{i + 1}",
            "title": f"Control {i + 1}",
            "framework": "ISO 27001",
            "desc": f"Description for control {i + 1}",
            "section_title": "Information Security",
        }
        for i in range(n)
    ]


SAMPLE_JSON_RESPONSE = json.dumps([
    {
        "control_id": "A.1",
        "control_title": "Control 1",
        "framework": "ISO 27001",
        "questions": [
            {
                "id": "q-abc123",
                "question": "Do you have a policy?",
                "category": "policy_existence",
                "priority": "high",
                "expected_evidence": "Policy document",
                "guidance_notes": "Check for formal approval",
            }
        ],
    }
])


SAMPLE_CONTEXT = {
    "organization_name": "Test Corp",
    "industry": "Technology",
    "project_id": "test-project",
}

SAMPLE_CRITERIA = {
    "maturity_level": "recurring_assessment",
    "question_depth": "balanced",
}


def _mock_response(text: str, cached: int = 0):
    """Create a mock Anthropic API response."""
    content_block = MagicMock()
    content_block.text = text
    content_block.__class__.__name__ = "TextBlock"
    # hasattr(block, "text") check
    type(content_block).text = property(lambda self: text)

    usage = MagicMock()
    usage.input_tokens = 1000
    usage.output_tokens = 500
    usage.cache_read_input_tokens = cached

    response = MagicMock()
    response.content = [content_block]
    response.usage = usage
    return response


# ── distribute_controls tests ────────────────────────────────────────


class TestDistributeControls:
    def test_even_split(self):
        controls = _make_controls(8)
        buckets = QuestionGenerationSwarm.distribute_controls(controls, 4)
        assert len(buckets) == 4
        assert all(len(b) == 2 for b in buckets)

    def test_uneven_split(self):
        controls = _make_controls(10)
        buckets = QuestionGenerationSwarm.distribute_controls(controls, 4)
        # 10 controls: 3, 3, 2, 2
        sizes = sorted([len(b) for b in buckets], reverse=True)
        assert sizes == [3, 3, 2, 2]

    def test_round_robin_order(self):
        controls = _make_controls(8)
        buckets = QuestionGenerationSwarm.distribute_controls(controls, 4)
        # Control 0 → bucket 0, control 1 → bucket 1, etc.
        assert buckets[0][0]["id"] == "A.1"
        assert buckets[1][0]["id"] == "A.2"
        assert buckets[2][0]["id"] == "A.3"
        assert buckets[3][0]["id"] == "A.4"
        # Second round
        assert buckets[0][1]["id"] == "A.5"
        assert buckets[1][1]["id"] == "A.6"

    def test_fewer_than_agents(self):
        controls = _make_controls(2)
        buckets = QuestionGenerationSwarm.distribute_controls(controls, 4)
        assert len(buckets) == 4
        assert len(buckets[0]) == 1
        assert len(buckets[1]) == 1
        assert len(buckets[2]) == 0
        assert len(buckets[3]) == 0

    def test_zero_controls(self):
        buckets = QuestionGenerationSwarm.distribute_controls([], 4)
        assert len(buckets) == 4
        assert all(len(b) == 0 for b in buckets)

    def test_single_agent(self):
        controls = _make_controls(5)
        buckets = QuestionGenerationSwarm.distribute_controls(controls, 1)
        assert len(buckets) == 1
        assert len(buckets[0]) == 5


# ── WorkerAgent tests ────────────────────────────────────────────────


class TestWorkerAgent:
    @pytest.mark.asyncio
    async def test_generate_single_batch(self):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(SAMPLE_JSON_RESPONSE)
        )

        worker = WorkerAgent(agent_id=0, client=mock_client, model="test-model")
        controls = _make_controls(5)
        shared_ctx = "Test shared context"

        generated, stats = await worker.generate(
            controls, shared_ctx, "test-session"
        )

        assert len(generated) == 1  # Our sample has 1 control
        assert stats.agent_id == 0
        assert stats.controls_assigned == 5
        assert stats.input_tokens == 1000
        assert stats.output_tokens == 500
        assert stats.error is None
        mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_uses_cache_control(self):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(SAMPLE_JSON_RESPONSE, cached=800)
        )

        worker = WorkerAgent(agent_id=1, client=mock_client, model="test-model")
        await worker.generate(_make_controls(3), "shared", "test-session")

        call_args = mock_client.messages.create.call_args
        system_blocks = call_args.kwargs["system"]
        assert len(system_blocks) == 2
        assert system_blocks[0]["cache_control"] == {"type": "ephemeral"}
        assert "cache_control" not in system_blocks[1]

    @pytest.mark.asyncio
    async def test_generate_empty_controls(self):
        mock_client = AsyncMock()
        worker = WorkerAgent(agent_id=0, client=mock_client, model="test-model")

        generated, stats = await worker.generate([], "shared", "test-session")

        assert generated == []
        assert stats.controls_assigned == 0
        mock_client.messages.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_api_failure(self):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=Exception("API error")
        )

        worker = WorkerAgent(agent_id=2, client=mock_client, model="test-model")
        # Patch tenacity to not retry (speeds up test)
        worker._call_api = AsyncMock(side_effect=Exception("API error"))

        generated, stats = await worker.generate(
            _make_controls(3), "shared", "test-session"
        )

        assert generated == []
        assert stats.error is not None
        assert "API error" in stats.error

    @pytest.mark.asyncio
    async def test_generate_progress_callback(self):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(SAMPLE_JSON_RESPONSE)
        )

        worker = WorkerAgent(agent_id=0, client=mock_client, model="test-model")
        callback_calls = []

        def on_progress(agent_id, controls_done, questions_generated):
            callback_calls.append((agent_id, controls_done, questions_generated))

        await worker.generate(
            _make_controls(5), "shared", "test-session", on_progress=on_progress
        )

        assert len(callback_calls) == 1
        assert callback_calls[0][0] == 0  # agent_id

    @pytest.mark.asyncio
    async def test_sub_batching(self):
        """Controls >30 should be split into sub-batches."""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(SAMPLE_JSON_RESPONSE)
        )

        worker = WorkerAgent(agent_id=0, client=mock_client, model="test-model")
        controls = _make_controls(35)

        await worker.generate(controls, "shared", "test-session")

        # 35 controls → 2 sub-batches (30 + 5)
        assert mock_client.messages.create.call_count == 2


# ── QuestionGenerationSwarm tests ────────────────────────────────────


class TestSwarm:
    @pytest.mark.asyncio
    async def test_generate_aggregates_results(self):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(SAMPLE_JSON_RESPONSE)
        )

        swarm = QuestionGenerationSwarm(
            client=mock_client, model="test-model", num_agents=4
        )
        result = await swarm.generate(
            _make_controls(8), SAMPLE_CONTEXT, SAMPLE_CRITERIA, "test-session"
        )

        assert isinstance(result, SwarmResult)
        # 4 agents each produce 1 control from our sample
        assert len(result.controls) == 4
        assert len(result.agent_stats) == 4
        assert result.total_input_tokens == 4000  # 1000 per agent
        assert result.total_output_tokens == 2000  # 500 per agent

    @pytest.mark.asyncio
    async def test_partial_failure(self):
        """One agent failing shouldn't prevent others from completing."""
        call_count = 0

        async def flaky_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Second agent fails
                raise Exception("Simulated failure")
            return _mock_response(SAMPLE_JSON_RESPONSE)

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=flaky_create)

        swarm = QuestionGenerationSwarm(
            client=mock_client, model="test-model", num_agents=4
        )
        # Patch workers to skip tenacity retries
        for worker in swarm._workers:
            original_call = worker._call_api

            async def patched_call(sc, cs, _orig=original_call):
                return await _orig(sc, cs)

            worker._call_api = patched_call

        result = await swarm.generate(
            _make_controls(8), SAMPLE_CONTEXT, SAMPLE_CRITERIA, "test-session"
        )

        # 3 successful agents produce results, 1 failed
        assert len(result.controls) == 3
        failed_stats = [s for s in result.agent_stats if s.error is not None]
        assert len(failed_stats) == 1

    @pytest.mark.asyncio
    async def test_generate_stream_events(self):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(SAMPLE_JSON_RESPONSE)
        )

        swarm = QuestionGenerationSwarm(
            client=mock_client, model="test-model", num_agents=2
        )
        result_out = SwarmResult()

        events = []
        async for event in swarm.generate_stream(
            _make_controls(4), SAMPLE_CONTEXT, SAMPLE_CRITERIA, "test-session",
            result_out=result_out,
        ):
            events.append(event)

        # Parse events
        progress_events = [e for e in events if "event: progress" in e]
        agent_complete_events = [e for e in events if "event: agent_complete" in e]

        # Initial progress + 2 agent progress events
        assert len(progress_events) == 3
        # 2 agent_complete events (one per agent)
        assert len(agent_complete_events) == 2

        # result_out should be populated
        assert len(result_out.controls) == 2

    @pytest.mark.asyncio
    async def test_generate_stream_result_out(self):
        """result_out should contain aggregated stats."""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(SAMPLE_JSON_RESPONSE, cached=500)
        )

        swarm = QuestionGenerationSwarm(
            client=mock_client, model="test-model", num_agents=2
        )
        result_out = SwarmResult()

        async for _ in swarm.generate_stream(
            _make_controls(4), SAMPLE_CONTEXT, SAMPLE_CRITERIA, "test-session",
            result_out=result_out,
        ):
            pass

        assert result_out.total_input_tokens == 2000
        assert result_out.total_cache_read_tokens == 1000
        assert result_out.total_output_tokens == 1000
        assert len(result_out.agent_stats) == 2


# ── Prompt building tests ────────────────────────────────────────────


class TestPrompts:
    def test_build_shared_context(self):
        ctx = build_shared_context(
            SAMPLE_CONTEXT,
            maturity_level="first_time_audit",
            question_depth="balanced",
        )
        assert "Test Corp" in ctx
        assert "Technology" in ctx
        assert "3 questions per control" in ctx
        assert "First Time Audit" in ctx
        assert "JSON array" in ctx

    def test_build_shared_context_with_options(self):
        ctx = build_shared_context(
            SAMPLE_CONTEXT,
            maturity_level="mature_isms",
            question_depth="detailed_technical",
            priority_domains=["Access Control"],
            compliance_concerns="Weak password policy",
            controls_to_skip="A.8.1",
            questions_per_control=5,
        )
        assert "5 questions per control" in ctx
        assert "Priority Focus Areas" in ctx
        assert "Access Control" in ctx
        assert "Weak password policy" in ctx
        assert "Controls to De-emphasize" in ctx

    def test_build_controls_section(self):
        text = build_controls_section("- A.1: Test control")
        assert "Controls to Process" in text
        assert "A.1: Test control" in text

    def test_format_batch_controls(self):
        controls = _make_controls(2)
        text = format_batch_controls(controls)
        assert "**A.1**" in text
        assert "**A.2**" in text
        assert "[ISO 27001]" in text
        assert "(Information Security)" in text


# ── Parsing tests ────────────────────────────────────────────────────


class TestParsing:
    def test_parse_questions_valid(self):
        controls = _parse_questions(SAMPLE_JSON_RESPONSE, "test")
        assert len(controls) == 1
        assert controls[0].control_id == "A.1"
        assert len(controls[0].questions) == 1
        assert controls[0].questions[0].id == "q-abc123"

    def test_parse_questions_fenced_json(self):
        text = f"Here are the questions:\n```json\n{SAMPLE_JSON_RESPONSE}\n```"
        controls = _parse_questions(text, "test")
        assert len(controls) == 1

    def test_parse_questions_invalid_json(self):
        controls = _parse_questions("not json at all", "test")
        assert controls == []

    def test_parse_questions_empty_response(self):
        controls = _parse_questions("", "test")
        assert controls == []

    def test_extract_json_array_basic(self):
        assert _extract_json_array('[{"a":1}]') == '[{"a":1}]'

    def test_extract_json_array_fenced(self):
        text = "```json\n[1,2,3]\n```"
        assert _extract_json_array(text) == "[1,2,3]"

    def test_extract_json_array_surrounded(self):
        text = "Here is the result: [1, 2, 3] and more text"
        assert _extract_json_array(text) == "[1, 2, 3]"

    def test_extract_json_array_none(self):
        assert _extract_json_array("no array here") is None

    def test_extract_json_array_nested(self):
        text = '[[1, 2], [3, 4]]'
        result = _extract_json_array(text)
        assert result == '[[1, 2], [3, 4]]'


# ── Token usage logging tests ────────────────────────────────────────


class TestTokenLogging:
    @pytest.mark.asyncio
    async def test_cache_read_tokens_tracked(self):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(SAMPLE_JSON_RESPONSE, cached=800)
        )

        worker = WorkerAgent(agent_id=0, client=mock_client, model="test")
        _, stats = await worker.generate(
            _make_controls(3), "shared", "test-session"
        )

        assert stats.cache_read_tokens == 800
        assert stats.input_tokens == 1000
        assert stats.output_tokens == 500
