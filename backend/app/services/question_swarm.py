"""6-agent question generation swarm (optimized for speed + quality).

Distributes controls across independent worker agents that generate
questions in parallel. Uses Anthropic prompt caching to reduce cost:
the shared context is cached across workers (90% discount on 2nd-4th).

OPTIMIZATIONS FOR PERFORMANCE:
1. Increased agents from 4 → 6 for better CPU parallelism
2. Dynamic batch size: scales inversely with questions_per_control to prevent truncation
3. max_tokens = 8192 (6144 caused truncation at 5 questions/control)
4. Reduced per-agent timeout from 180s → 120s (tighter deadline)
5. Simplified system prompt in question_swarm_prompts.py (~40% smaller)
6. Made model configurable (supports fast Haiku for quick iterations)
7. Truncated JSON recovery: salvages partial results instead of returning 0 questions

EXPECTED IMPROVEMENTS:
- Current: ~4 minutes for 18 questions
- Target: <2 minutes (with optimized prompts + more agents)
- Model switch to Haiku: 3-5x faster but lower quality (dev/testing only)

See question_swarm_prompts.py for prompt caching explanation.
"""

import asyncio
import json
import logging
import time
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

_MAX_OUTPUT_TOKENS = 8192  # Upper cap for dynamic max_tokens calculation
DEFAULT_NUM_AGENTS = 6  # Fallback cap; actual count is adaptive via _optimal_worker_count
MAX_CONTROLS_PER_CALL = 20  # Max controls per API call
_TOKENS_PER_QUESTION = 100  # ~90-100 actual tokens per question (longer professional phrasing)


def _effective_batch_size(questions_per_control: int) -> int:
    """Compute sub-batch size that fits within the output token budget.

    Scales inversely with questions_per_control so high-question runs
    don't truncate mid-JSON.  Examples:
      5 qpc → ~12 controls/call
      3 qpc → ~20 controls/call  (same as MAX_CONTROLS_PER_CALL)
      2 qpc → ~30 controls/call  (capped to MAX_CONTROLS_PER_CALL)
    """
    headroom = 0.75  # 25% safety margin
    max_controls = int(
        _MAX_OUTPUT_TOKENS * headroom / (questions_per_control * _TOKENS_PER_QUESTION)
    )
    return max(5, min(max_controls, MAX_CONTROLS_PER_CALL))


def _dynamic_max_tokens(num_controls: int, qpc: int) -> int:
    """Calculate max_tokens based on expected output size.

    Formula: (controls * (qpc * tokens_per_q + overhead)) * 1.5 safety margin.
    Capped between 1024 and _MAX_OUTPUT_TOKENS.
    """
    overhead_per_control = 200  # JSON structure, control_id, title, framework
    raw = num_controls * (qpc * _TOKENS_PER_QUESTION + overhead_per_control)
    with_margin = int(raw * 1.5)
    return max(1024, min(with_margin, _MAX_OUTPUT_TOKENS))


def _optimal_worker_count(num_controls: int) -> int:
    """Choose worker count based on control count to reduce overhead."""
    if num_controls < 10:
        return 2
    elif num_controls < 30:
        return 3
    elif num_controls < 60:
        return 4
    return 6


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
        questions_per_control: int = 3,
    ) -> tuple[list[ControlQuestions], AgentStats]:
        """Generate questions for assigned controls.

        Args:
            controls: List of control dicts to process.
            shared_context: The cacheable shared system prompt.
            session_id: Parent session ID for logging.
            on_progress: Callback(agent_id, controls_done, questions_generated).
            questions_per_control: Number of questions per control (affects batch size).

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

        # Dynamic sub-batch size: fewer controls per call when questions_per_control is high
        batch_size = _effective_batch_size(questions_per_control)
        if len(controls) > batch_size:
            sub_batches = [
                controls[i : i + batch_size]
                for i in range(0, len(controls), batch_size)
            ]
        else:
            sub_batches = [controls]

        all_generated: list[ControlQuestions] = []

        for sub_idx, sub_batch in enumerate(sub_batches):
            batch_text = format_batch_controls(sub_batch)
            controls_section = build_controls_section(batch_text)

            try:
                batch_max_tokens = _dynamic_max_tokens(len(sub_batch), questions_per_control)
                api_t0 = time.perf_counter()
                result, usage = await self._call_api(
                    shared_context, controls_section, max_tokens=batch_max_tokens
                )
                api_ms = int((time.perf_counter() - api_t0) * 1000)

                stats.input_tokens += usage.get("input_tokens", 0)
                stats.cache_read_tokens += usage.get("cache_read_input_tokens", 0)
                stats.output_tokens += usage.get("output_tokens", 0)

                parsed = _parse_questions(result, session_id)
                trimmed = _validate_and_trim_questions(parsed)
                all_generated.extend(trimmed)

                batch_q = sum(len(c.questions) for c in trimmed)
                stats.controls_generated += len(trimmed)
                stats.questions_generated += batch_q

                logger.info(
                    f"Agent {self.agent_id} sub-batch {sub_idx + 1}/{len(sub_batches)}: "
                    f"{len(trimmed)} controls, {batch_q} questions in {api_ms}ms "
                    f"(max_tokens={batch_max_tokens}) | "
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
            on_progress(
                self.agent_id, stats.controls_generated, stats.questions_generated
            )

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
        self,
        shared_context: str,
        controls_section: str,
        *,
        max_tokens: int = _MAX_OUTPUT_TOKENS,
    ) -> tuple[str, dict]:
        """Make the API call with prompt caching on the shared context."""
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
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
        effective_agents = min(_optimal_worker_count(len(controls)), self._num_agents)
        workers = [
            WorkerAgent(agent_id=i, client=self._client, model=self._model)
            for i in range(effective_agents)
        ]
        buckets = self.distribute_controls(controls, effective_agents)

        shared_context = build_shared_context(
            context,
            maturity_level=criteria.get("maturity_level", "recurring_assessment"),
            question_depth=criteria.get("question_depth", "balanced"),
            priority_domains=criteria.get("priority_domains"),
            compliance_concerns=criteria.get("compliance_concerns"),
            controls_to_skip=criteria.get("controls_to_skip"),
            questions_per_control=criteria.get("questions_per_control"),
        )

        qpc = criteria.get("questions_per_control", 3)

        swarm_t0 = time.perf_counter()
        logger.info(
            f"Swarm starting: {len(controls)} controls → "
            f"{effective_agents} agents "
            f"({', '.join(str(len(b)) for b in buckets)} controls each) "
            f"[{qpc} qpc, batch_size={_effective_batch_size(qpc)}]"
        )

        tasks = [
            worker.generate(
                bucket,
                shared_context,
                session_id,
                questions_per_control=qpc,
            )
            for worker, bucket in zip(workers, buckets)
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

        swarm_ms = int((time.perf_counter() - swarm_t0) * 1000)
        total_q = sum(s.questions_generated for s in swarm_result.agent_stats)
        logger.info(
            f"Swarm complete: {swarm_ms}ms wall-clock, "
            f"{len(swarm_result.controls)} controls, {total_q} questions, "
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
        effective_agents = min(_optimal_worker_count(len(controls)), self._num_agents)
        workers = [
            WorkerAgent(agent_id=i, client=self._client, model=self._model)
            for i in range(effective_agents)
        ]
        buckets = self.distribute_controls(controls, effective_agents)
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

        qpc = criteria.get("questions_per_control", 3)

        swarm_t0 = time.perf_counter()
        logger.info(
            f"Swarm stream starting: {total_controls} controls → "
            f"{effective_agents} agents "
            f"[{qpc} qpc, batch_size={_effective_batch_size(qpc)}]"
        )

        # Initial progress
        yield _sse(
            "progress",
            {
                "batch": 0,
                "total": effective_agents,
                "controls_done": 0,
                "total_controls": total_controls,
                "agents_complete": 0,
                "total_agents": effective_agents,
            },
        )

        # Progress queue for agent completions
        progress_queue: asyncio.Queue[
            tuple[int, list[ControlQuestions], AgentStats]
        ] = asyncio.Queue()

        async def _worker_wrapper(worker: WorkerAgent, bucket: list[dict]) -> None:
            try:
                generated, stats = await worker.generate(
                    bucket,
                    shared_context,
                    session_id,
                    questions_per_control=qpc,
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
                    for worker, bucket in zip(workers, buckets)
                ],
                return_exceptions=True,
            )
        )

        # Collect results as they arrive
        agents_done = 0
        controls_done = 0
        all_controls: list[ControlQuestions] = []
        all_stats: list[AgentStats] = []

        while agents_done < effective_agents:
            try:
                agent_id, generated, stats = await asyncio.wait_for(
                    progress_queue.get(),
                    timeout=90.0,  # Tightened: smaller output = faster completion
                )
            except asyncio.TimeoutError:
                yield _sse(
                    "error", {"error": "Agent timed out after 90s"}
                )
                return

            agents_done += 1
            controls_done += stats.controls_generated
            all_controls.extend(generated)
            all_stats.append(stats)

            # Emit agent_complete event (includes controls for early rendering)
            yield _sse(
                "agent_complete",
                {
                    "agent_id": agent_id,
                    "agent_label": f"Agent {agent_id + 1}",
                    "controls_generated": stats.controls_generated,
                    "questions_generated": stats.questions_generated,
                    "controls": [c.model_dump() for c in generated],
                },
            )

            # Emit progress event (backward-compatible batch/total)
            yield _sse(
                "progress",
                {
                    "batch": agents_done,
                    "total": effective_agents,
                    "controls_done": controls_done,
                    "total_controls": total_controls,
                    "agent_id": agent_id,
                    "agents_complete": agents_done,
                    "total_agents": effective_agents,
                },
            )

        # Ensure gather completes
        await gather_task

        swarm_ms = int((time.perf_counter() - swarm_t0) * 1000)
        total_q = sum(s.questions_generated for s in all_stats)
        logger.info(
            f"Swarm stream complete: {swarm_ms}ms wall-clock, "
            f"{controls_done} controls, {total_q} questions"
        )

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
        logger.warning(
            f"Session {session_id}: JSON parse error: {e} — attempting repair"
        )
        repaired = _try_repair_truncated_json(json_str)
        if repaired:
            try:
                raw = json.loads(repaired)
                logger.info(
                    f"Session {session_id}: Repaired truncated JSON: "
                    f"salvaged {len(raw)} controls"
                )
            except json.JSONDecodeError:
                logger.error(f"Session {session_id}: JSON repair also failed")
                return []
        else:
            logger.error(f"Session {session_id}: Could not repair truncated JSON")
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


def _validate_and_trim_questions(
    controls: list[ControlQuestions],
) -> list[ControlQuestions]:
    """Post-generation validation: enforce word limits and strip guidance_notes."""
    max_question_words = 50  # Soft ceiling above the 45-word prompt target
    max_evidence_words = 8
    trimmed_count = 0

    for control in controls:
        for q in control.questions:
            # Truncate overly verbose questions
            words = q.question.split()
            if len(words) > max_question_words:
                q.question = " ".join(words[:max_question_words]) + "?"
                trimmed_count += 1

            # Strip guidance_notes (safety net if model still generates them)
            if q.guidance_notes:
                q.guidance_notes = None

            # Trim expected_evidence to max words
            if q.expected_evidence:
                ev_words = q.expected_evidence.split()
                if len(ev_words) > max_evidence_words:
                    q.expected_evidence = " ".join(ev_words[:max_evidence_words])

    if trimmed_count > 0:
        logger.info(
            f"Post-validation: trimmed {trimmed_count} questions exceeding "
            f"{max_question_words} words"
        )

    return controls


def _try_repair_truncated_json(json_str: str) -> str | None:
    """Attempt to repair a truncated JSON array by removing the incomplete trailing entry.

    Handles edge cases where truncation lands inside a string value (unbalanced
    quotes) by progressively stripping from the end until valid JSON is found.
    """
    # Strategy 1: Find the last complete object boundary "},"
    last_comma = json_str.rfind("},")
    if last_comma != -1:
        candidate = json_str[: last_comma + 1] + "]"
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass  # Fall through to more aggressive strategies

    # Strategy 2: Find the last "}" and close the array there
    last_brace = json_str.rfind("}")
    if last_brace != -1:
        bracket = json_str.find("[")
        if bracket != -1 and last_brace > bracket:
            candidate = json_str[: last_brace + 1] + "]"
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass

    # Strategy 3: Progressive strip — walk backwards through "}," boundaries
    # to find the deepest valid prefix. Handles cases where truncation inside
    # a string value creates unbalanced quotes in the last complete-looking object.
    search_from = len(json_str)
    for _ in range(20):  # Cap iterations to avoid infinite loop
        pos = json_str.rfind("},", 0, search_from)
        if pos == -1:
            break
        candidate = json_str[: pos + 1] + "]"
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            search_from = pos  # Try the next "}," further back

    return None


def _extract_json_array(text: str) -> str | None:
    """Find the outermost JSON array in a text blob."""
    import re

    text = text.strip()

    # Try fenced code block first
    fence_match = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text, re.IGNORECASE)
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
