"""4-agent question generation swarm.

Distributes controls across independent worker agents that generate
questions in parallel.  Uses Anthropic prompt caching to reduce cost:
the shared context is cached across workers (90% discount on 2nd-4th).
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import AsyncGenerator, Callable

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from app.models.questionnaire import ControlQuestions, GeneratedQuestion
from app.services.question_swarm_prompts import (
    build_controls_section,
    build_shared_context,
    format_batch_controls,
)

logger = logging.getLogger(__name__)

CRITERIA_MAX_TOKENS = 8192
DEFAULT_NUM_AGENTS = 4
MAX_CONTROLS_PER_CALL = 30  # Sub-batch threshold


# ── Result types ─────────────────────────────────────────────────────


@dataclass
class AgentStats:
    """Per-agent generation statistics."""

    agent_id: int
    controls_assigned: int = 0
    controls_generated: int = 0
    questions_generated: int = 0
    input_tokens: int = 0
    cache_read_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None


@dataclass
class SwarmResult:
    """Aggregated results from all workers."""

    controls: list[ControlQuestions] = field(default_factory=list)
    agent_stats: list[AgentStats] = field(default_factory=list)
    total_input_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_output_tokens: int = 0


# ── Worker Agent ─────────────────────────────────────────────────────


class WorkerAgent:
    """A single worker that generates questions for its assigned controls."""

    def __init__(
        self,
        agent_id: int,
        client: anthropic.AsyncAnthropic,
        model: str,
    ) -> None:
        self.agent_id = agent_id
        self._client = client
        self._model = model

    async def generate(
        self,
        controls: list[dict],
        shared_context: str,
        session_id: str,
        on_progress: Callable[[int, int, int], None] | None = None,
    ) -> tuple[list[ControlQuestions], AgentStats]:
        """Generate questions for assigned controls.

        Args:
            controls: List of control dicts to process.
            shared_context: The cacheable shared system prompt.
            session_id: Parent session ID for logging.
            on_progress: Callback(agent_id, controls_done, questions_generated).

        Returns:
            Tuple of (generated controls, agent stats).
        """
        stats = AgentStats(
            agent_id=self.agent_id,
            controls_assigned=len(controls),
        )

        if not controls:
            if on_progress:
                on_progress(self.agent_id, 0, 0)
            return [], stats

        # Sub-batch if a worker has >MAX_CONTROLS_PER_CALL controls
        if len(controls) > MAX_CONTROLS_PER_CALL:
            sub_batches = [
                controls[i : i + MAX_CONTROLS_PER_CALL]
                for i in range(0, len(controls), MAX_CONTROLS_PER_CALL)
            ]
        else:
            sub_batches = [controls]

        all_generated: list[ControlQuestions] = []

        for sub_idx, sub_batch in enumerate(sub_batches):
            batch_text = format_batch_controls(sub_batch)
            controls_section = build_controls_section(batch_text)

            try:
                result, usage = await self._call_api(shared_context, controls_section)
                stats.input_tokens += usage.get("input_tokens", 0)
                stats.cache_read_tokens += usage.get("cache_read_input_tokens", 0)
                stats.output_tokens += usage.get("output_tokens", 0)

                parsed = _parse_questions(result, session_id)
                all_generated.extend(parsed)

                batch_q = sum(len(c.questions) for c in parsed)
                stats.controls_generated += len(parsed)
                stats.questions_generated += batch_q

                logger.info(
                    f"Agent {self.agent_id} sub-batch {sub_idx + 1}/{len(sub_batches)}: "
                    f"{len(parsed)} controls, {batch_q} questions | "
                    f"input={usage.get('input_tokens', 0)} "
                    f"(cached={usage.get('cache_read_input_tokens', 0)}) "
                    f"output={usage.get('output_tokens', 0)}"
                )

            except Exception as e:
                logger.error(
                    f"Agent {self.agent_id} sub-batch {sub_idx + 1} failed: {e}"
                )
                stats.error = str(e)
                continue

        if on_progress:
            on_progress(self.agent_id, stats.controls_generated, stats.questions_generated)

        return all_generated, stats

    @retry(
        retry=retry_if_exception_type(
            (anthropic.RateLimitError, anthropic.APITimeoutError)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _call_api(
        self, shared_context: str, controls_section: str
    ) -> tuple[str, dict]:
        """Make the API call with prompt caching on the shared context."""
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=CRITERIA_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": shared_context,
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": controls_section,
                },
            ],
            messages=[
                {
                    "role": "user",
                    "content": "Generate the compliance assessment questions for these specific controls.",
                }
            ],
        )

        text = "".join(b.text for b in response.content if hasattr(b, "text"))

        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cache_read_input_tokens": getattr(
                response.usage, "cache_read_input_tokens", 0
            )
            or 0,
        }

        return text, usage


# ── Swarm Coordinator ────────────────────────────────────────────────


class QuestionGenerationSwarm:
    """Coordinates multiple WorkerAgents to generate questions in parallel."""

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str,
        num_agents: int = DEFAULT_NUM_AGENTS,
    ) -> None:
        self._client = client
        self._model = model
        self._num_agents = num_agents
        self._workers = [
            WorkerAgent(agent_id=i, client=client, model=model)
            for i in range(num_agents)
        ]

    @staticmethod
    def distribute_controls(
        controls: list[dict], num_agents: int = DEFAULT_NUM_AGENTS
    ) -> list[list[dict]]:
        """Round-robin distribution of controls across agents."""
        buckets: list[list[dict]] = [[] for _ in range(num_agents)]
        for i, control in enumerate(controls):
            buckets[i % num_agents].append(control)
        return buckets

    async def generate(
        self,
        controls: list[dict],
        context: dict,
        criteria: dict,
        session_id: str,
    ) -> SwarmResult:
        """Run all workers in parallel and aggregate results."""
        buckets = self.distribute_controls(controls, self._num_agents)

        shared_context = build_shared_context(
            context,
            maturity_level=criteria.get("maturity_level", "recurring_assessment"),
            question_depth=criteria.get("question_depth", "balanced"),
            priority_domains=criteria.get("priority_domains"),
            compliance_concerns=criteria.get("compliance_concerns"),
            controls_to_skip=criteria.get("controls_to_skip"),
            questions_per_control=criteria.get("questions_per_control"),
        )

        logger.info(
            f"Swarm starting: {len(controls)} controls → "
            f"{self._num_agents} agents "
            f"({', '.join(str(len(b)) for b in buckets)} controls each)"
        )

        tasks = [
            worker.generate(bucket, shared_context, session_id)
            for worker, bucket in zip(self._workers, buckets)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        swarm_result = SwarmResult()
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Agent {i} failed entirely: {result}")
                swarm_result.agent_stats.append(
                    AgentStats(
                        agent_id=i,
                        controls_assigned=len(buckets[i]),
                        error=str(result),
                    )
                )
                continue
            generated, stats = result
            swarm_result.controls.extend(generated)
            swarm_result.agent_stats.append(stats)
            swarm_result.total_input_tokens += stats.input_tokens
            swarm_result.total_cache_read_tokens += stats.cache_read_tokens
            swarm_result.total_output_tokens += stats.output_tokens

        logger.info(
            f"Swarm complete: {len(swarm_result.controls)} controls, "
            f"tokens: input={swarm_result.total_input_tokens} "
            f"(cached={swarm_result.total_cache_read_tokens}) "
            f"output={swarm_result.total_output_tokens}"
        )

        return swarm_result

    async def generate_stream(
        self,
        controls: list[dict],
        context: dict,
        criteria: dict,
        session_id: str,
        result_out: SwarmResult | None = None,
    ) -> AsyncGenerator[str, None]:
        """Run workers in parallel, yielding SSE events as each completes.

        Args:
            result_out: Optional SwarmResult that will be populated in-place
                with the aggregated results.  Avoids needing a second
                ``generate()`` call after streaming.
        """
        buckets = self.distribute_controls(controls, self._num_agents)
        total_controls = len(controls)

        shared_context = build_shared_context(
            context,
            maturity_level=criteria.get("maturity_level", "recurring_assessment"),
            question_depth=criteria.get("question_depth", "balanced"),
            priority_domains=criteria.get("priority_domains"),
            compliance_concerns=criteria.get("compliance_concerns"),
            controls_to_skip=criteria.get("controls_to_skip"),
            questions_per_control=criteria.get("questions_per_control"),
        )

        logger.info(
            f"Swarm stream starting: {total_controls} controls → "
            f"{self._num_agents} agents"
        )

        # Initial progress
        yield _sse("progress", {
            "batch": 0,
            "total": self._num_agents,
            "controls_done": 0,
            "total_controls": total_controls,
            "agents_complete": 0,
            "total_agents": self._num_agents,
        })

        # Progress queue for agent completions
        progress_queue: asyncio.Queue[tuple[int, list[ControlQuestions], AgentStats]] = (
            asyncio.Queue()
        )

        async def _worker_wrapper(
            worker: WorkerAgent, bucket: list[dict]
        ) -> None:
            try:
                generated, stats = await worker.generate(
                    bucket, shared_context, session_id
                )
                await progress_queue.put((worker.agent_id, generated, stats))
            except Exception as e:
                error_stats = AgentStats(
                    agent_id=worker.agent_id,
                    controls_assigned=len(bucket),
                    error=str(e),
                )
                await progress_queue.put((worker.agent_id, [], error_stats))

        # Launch all workers
        gather_task = asyncio.ensure_future(
            asyncio.gather(
                *[
                    _worker_wrapper(worker, bucket)
                    for worker, bucket in zip(self._workers, buckets)
                ],
                return_exceptions=True,
            )
        )

        # Collect results as they arrive
        agents_done = 0
        controls_done = 0
        all_controls: list[ControlQuestions] = []
        all_stats: list[AgentStats] = []

        while agents_done < self._num_agents:
            try:
                agent_id, generated, stats = await asyncio.wait_for(
                    progress_queue.get(), timeout=180.0
                )
            except asyncio.TimeoutError:
                yield _sse("error", {"error": "Agent processing timed out"})
                return

            agents_done += 1
            controls_done += stats.controls_generated
            all_controls.extend(generated)
            all_stats.append(stats)

            # Emit agent_complete event
            yield _sse("agent_complete", {
                "agent_id": agent_id,
                "agent_label": f"Agent {agent_id + 1}",
                "controls_generated": stats.controls_generated,
                "questions_generated": stats.questions_generated,
            })

            # Emit progress event (backward-compatible batch/total)
            yield _sse("progress", {
                "batch": agents_done,
                "total": self._num_agents,
                "controls_done": controls_done,
                "total_controls": total_controls,
                "agent_id": agent_id,
                "agents_complete": agents_done,
                "total_agents": self._num_agents,
            })

        # Ensure gather completes
        await gather_task

        # Populate result_out if provided
        if result_out is not None:
            result_out.controls = all_controls
            result_out.agent_stats = all_stats
            result_out.total_input_tokens = sum(s.input_tokens for s in all_stats)
            result_out.total_cache_read_tokens = sum(
                s.cache_read_tokens for s in all_stats
            )
            result_out.total_output_tokens = sum(s.output_tokens for s in all_stats)


# ── Shared utilities ─────────────────────────────────────────────────


def _sse(event: str, data: dict) -> str:
    """Format a single SSE event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _parse_questions(text: str, session_id: str) -> list[ControlQuestions]:
    """Extract JSON questions array from Claude's response."""
    json_str = _extract_json_array(text)
    if not json_str:
        logger.error(f"Session {session_id}: Could not extract JSON from response")
        return []

    try:
        raw = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"Session {session_id}: JSON parse error: {e}")
        return []

    controls = []
    for item in raw:
        questions = []
        for q in item.get("questions", []):
            questions.append(
                GeneratedQuestion(
                    id=q.get("id", f"q-{uuid.uuid4().hex[:8]}"),
                    question=q.get("question", ""),
                    category=q.get("category", "general"),
                    priority=q.get("priority", "medium"),
                    expected_evidence=q.get("expected_evidence"),
                    guidance_notes=q.get("guidance_notes"),
                )
            )
        controls.append(
            ControlQuestions(
                control_id=item.get("control_id", ""),
                control_title=item.get("control_title", ""),
                framework=item.get("framework", ""),
                questions=questions,
            )
        )

    return controls


def _extract_json_array(text: str) -> str | None:
    """Find the outermost JSON array in a text blob."""
    import re

    text = text.strip()

    # Try fenced code block first
    fence_match = re.search(
        r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text, re.IGNORECASE
    )
    if fence_match:
        return fence_match.group(1)

    # Fallback: bracket matching
    start = text.find("[")
    if start == -1:
        return None

    depth = 0
    for i in range(start, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    # Last resort: first [ to last ]
    end = text.rfind("]")
    if end != -1 and end > start:
        return text[start : end + 1]
    return None
