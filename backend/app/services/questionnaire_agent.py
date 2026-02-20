"""Questionnaire Agent — conversational compliance question generator.

Uses Claude Opus 4.6 with tool_use to interview the user about their
question generation criteria, then generates tailored compliance questions
for all selected framework controls.
"""

import asyncio
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import anthropic
import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.models.questionnaire import (
    AgentQuestion,
    ControlQuestions,
    QuestionnaireComplete,
    QuestionnaireResponse,
)
from app.services.question_swarm import (
    QuestionGenerationSwarm,
    _extract_json_array as extract_json_array,
    _parse_questions as parse_questions,
)
from app.services.question_swarm_prompts import (
    format_batch_controls as _fmt_controls,
)

logger = logging.getLogger(__name__)

# Claude model for question generation
DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
MAX_TOKENS = 8192
CRITERIA_MAX_TOKENS = 8192  # Batch generation needs much more output space
MAX_CONCURRENT_BATCHES = 3  # Cap parallel API calls to respect rate limits

# Tool definition for the conversational loop
TOOLS = [
    {
        "name": "askQuestionToMe",
        "description": (
            "Ask the user a clarifying question about how compliance questions "
            "should be generated. Use this to understand their priorities, focus "
            "areas, depth preferences, and any specific concerns before generating "
            "questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask the user",
                },
                "context": {
                    "type": "string",
                    "description": (
                        "Brief explanation of why this information helps "
                        "generate better questions"
                    ),
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional suggested answers (user can also give free-text)"
                    ),
                },
            },
            "required": ["question"],
        },
    },
    {
        "name": "generateQuestionnaire",
        "description": (
            "Call this when you have collected enough information from the user "
            "and are ready to generate the compliance assessment questions. "
            "Pass the criteria you gathered from the conversation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "maturity_level": {
                    "type": "string",
                    "enum": [
                        "first_assessment",
                        "early_stage",
                        "developing",
                        "recurring_assessment",
                        "mature",
                    ],
                    "description": "The organization's compliance maturity level based on conversation",
                },
                "question_depth": {
                    "type": "string",
                    "enum": [
                        "high_level_overview",
                        "balanced",
                        "detailed_technical",
                    ],
                    "description": "How detailed the questions should be",
                },
                "priority_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Control domains to prioritize (e.g. ['A.5', 'A.8'] for ISO "
                        "or section titles for BNM). Empty array for all."
                    ),
                },
                "compliance_concerns": {
                    "type": "string",
                    "description": "Specific compliance concerns or known gaps mentioned by the user",
                },
                "criteria_summary": {
                    "type": "string",
                    "description": "A brief human-readable summary of the generation criteria gathered",
                },
                "questions_per_control": {
                    "type": "integer",
                    "description": "Number of questions to generate per control, as specified by the user. Options: 2, 3, or 5.",
                    "enum": [2, 3, 5],
                },
            },
            "required": ["maturity_level", "question_depth", "criteria_summary"],
        },
    },
]


@dataclass
class QuestionnaireSession:
    """In-memory state for an active questionnaire session."""

    session_id: str
    project_id: str
    client_id: str
    user_id: str
    assessment_id: Optional[str] = None
    messages: list[dict] = field(default_factory=list)
    pending_tool_use_id: Optional[str] = None
    project_context: dict = field(default_factory=dict)
    system_prompt: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at_ms: int = 0
    status: str = "active"


# Session store (in-memory; sessions lost on restart)
_sessions: dict[str, QuestionnaireSession] = {}

# Framework controls cache (avoids repeated full-table scans)
_controls_cache: dict[str, tuple[float, list]] = {}
CONTROLS_CACHE_TTL = 3600  # 1 hour

# Singleton
_agent: Optional["QuestionnaireAgent"] = None
_agent_lock = asyncio.Lock()


async def get_questionnaire_agent() -> "QuestionnaireAgent":
    """Get or create the singleton QuestionnaireAgent."""
    global _agent
    if _agent is not None:
        return _agent
    async with _agent_lock:
        if _agent is None:
            _agent = QuestionnaireAgent()
        return _agent


class QuestionnaireAgent:
    """Conversational agent that interviews users then generates questions."""

    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.claude_model or DEFAULT_MODEL
        
        # Diagnostic logging
        key_exists = bool(settings.anthropic_api_key)
        key_len = len(settings.anthropic_api_key) if settings.anthropic_api_key else 0
        logger.info(f"Initializing QuestionnaireAgent with model: {self._model}")
        logger.info(f"Anthropic API key exists: {key_exists}, length: {key_len}")
        
        # Disable HTTP/2 to avoid connection issues on some networks (common Mac issue)
        # Use a custom httpx client for more control
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(600.0, connect=30.0, read=570.0),
            http2=False, # Force HTTP/1.1
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            http_client=http_client
        )
        self._swarm = QuestionGenerationSwarm(
            client=self._client, model=self._model
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start_session(
        self, project_id: str, user_id: str, assessment_id: str | None = None
    ) -> QuestionnaireResponse:
        """Start a new questionnaire session.

        Fetches project context in parallel, builds the system prompt, and
        makes the first Claude call.  The agent will typically use the
        ``askQuestionToMe`` tool to ask the user a clarifying question.
        """
        session_id = str(uuid.uuid4())
        started_at = int(time.time() * 1000)

        # Fetch all context in parallel
        context = await self._fetch_project_context(project_id)

        client_id = context.get("client_id", "")
        system_prompt = self._build_system_prompt(context)

        session = QuestionnaireSession(
            session_id=session_id,
            project_id=project_id,
            client_id=client_id,
            user_id=user_id,
            assessment_id=assessment_id,
            system_prompt=system_prompt,
            project_context=context,
            started_at_ms=started_at,
        )

        # Initial user message to kick off the conversation
        session.messages.append(
            {
                "role": "user",
                "content": (
                    "I'd like to generate compliance assessment questions for "
                    "this project. Please start by understanding my requirements."
                ),
            }
        )

        _sessions[session_id] = session
        return await self._call_agent(session)

    async def generate_with_criteria(
        self,
        project_id: str,
        user_id: str,
        maturity_level: str,
        question_depth: str,
        priority_domains: list[str],
        compliance_concerns: str | None = None,
        controls_to_skip: str | None = None,
        assessment_id: str | None = None,
    ) -> QuestionnaireComplete:
        """Generate questions from structured wizard criteria (no chat loop).

        Fetches project context, builds a criteria-enriched prompt, and calls
        Claude in batches to generate questions for all controls.
        """
        session_id = str(uuid.uuid4())
        started_at = int(time.time() * 1000)

        # Return cached result if a completed session already exists
        if assessment_id:
            existing = await self._get_existing_session(assessment_id)
            if existing:
                logger.info(f"Returning cached questionnaire for assessment {assessment_id}")
                return existing

        context = await self._fetch_project_context(project_id)
        client_id = context.get("client_id", "")

        # Prepare for batching
        all_controls = self._build_controls_list(context)

        # Filter controls when priority_domains is specified
        if priority_domains:
            all_controls = self._filter_controls(all_controls, priority_domains)
            logger.info(
                f"Filtered to {len(all_controls)} controls for priority domains: {priority_domains}"
            )

        if not all_controls:
            logger.warning(f"No controls found for project {project_id}")
            return QuestionnaireComplete(
                session_id=session_id,
                controls=[],
                total_controls=0,
                total_questions=0,
                generation_time_ms=int(time.time() * 1000) - started_at,
                criteria_summary="No controls selected"
            )

        criteria_summary = self._build_criteria_summary(
            maturity_level=maturity_level,
            question_depth=question_depth,
            priority_domains=priority_domains,
            compliance_concerns=compliance_concerns,
            controls_to_skip=controls_to_skip,
        )

        session = QuestionnaireSession(
            session_id=session_id,
            project_id=project_id,
            client_id=client_id,
            user_id=user_id,
            assessment_id=assessment_id,
            project_context=context,
            started_at_ms=started_at,
        )
        _sessions[session_id] = session

        # Use swarm for parallel generation across 4 agents
        criteria_dict = {
            "maturity_level": maturity_level,
            "question_depth": question_depth,
            "priority_domains": priority_domains,
            "compliance_concerns": compliance_concerns,
            "controls_to_skip": controls_to_skip,
        }
        swarm_result = await self._swarm.generate(
            all_controls, context, criteria_dict, session_id
        )
        all_generated_controls = swarm_result.controls

        # Final result assembly
        total_questions = sum(len(c.questions) for c in all_generated_controls)
        elapsed_ms = int(time.time() * 1000) - started_at
        session.status = "completed"

        # Persist all results
        await self._persist_results(
            session, all_generated_controls, total_questions, elapsed_ms, criteria_summary
        )

        return QuestionnaireComplete(
            session_id=session_id,
            controls=all_generated_controls,
            total_controls=len(all_generated_controls),
            total_questions=total_questions,
            generation_time_ms=elapsed_ms,
            criteria_summary=criteria_summary,
        )

    async def generate_with_criteria_stream(
        self,
        project_id: str,
        user_id: str,
        maturity_level: str,
        question_depth: str,
        priority_domains: list[str],
        compliance_concerns: str | None = None,
        controls_to_skip: str | None = None,
        assessment_id: str | None = None,
    ):
        """Stream SSE events as batches complete during question generation."""
        session_id = str(uuid.uuid4())
        started_at = int(time.time() * 1000)

        # Check for cached session
        if assessment_id:
            existing = await self._get_existing_session(assessment_id)
            if existing:
                yield f"event: complete\ndata: {json.dumps(existing.model_dump())}\n\n"
                return

        context = await self._fetch_project_context(project_id)
        client_id = context.get("client_id", "")

        all_controls = self._build_controls_list(context)
        if priority_domains:
            all_controls = self._filter_controls(all_controls, priority_domains)

        if not all_controls:
            empty = QuestionnaireComplete(
                session_id=session_id,
                controls=[],
                total_controls=0,
                total_questions=0,
                generation_time_ms=int(time.time() * 1000) - started_at,
                criteria_summary="No controls selected",
            )
            yield f"event: complete\ndata: {json.dumps(empty.model_dump())}\n\n"
            return

        criteria_summary = self._build_criteria_summary(
            maturity_level=maturity_level,
            question_depth=question_depth,
            priority_domains=priority_domains,
            compliance_concerns=compliance_concerns,
            controls_to_skip=controls_to_skip,
        )

        session = QuestionnaireSession(
            session_id=session_id,
            project_id=project_id,
            client_id=client_id,
            user_id=user_id,
            assessment_id=assessment_id,
            project_context=context,
            started_at_ms=started_at,
        )
        _sessions[session_id] = session

        # Stream progress from swarm agents
        criteria_dict = {
            "maturity_level": maturity_level,
            "question_depth": question_depth,
            "priority_domains": priority_domains,
            "compliance_concerns": compliance_concerns,
            "controls_to_skip": controls_to_skip,
        }

        from app.services.question_swarm import SwarmResult
        swarm_result = SwarmResult()
        async for event in self._swarm.generate_stream(
            all_controls, context, criteria_dict, session_id,
            result_out=swarm_result,
        ):
            yield event

        all_generated_controls = swarm_result.controls

        total_questions = sum(len(c.questions) for c in all_generated_controls)
        elapsed_ms = int(time.time() * 1000) - started_at
        session.status = "completed"

        await self._persist_results(
            session, all_generated_controls, total_questions, elapsed_ms, criteria_summary
        )

        complete = QuestionnaireComplete(
            session_id=session_id,
            controls=all_generated_controls,
            total_controls=len(all_generated_controls),
            total_questions=total_questions,
            generation_time_ms=elapsed_ms,
            criteria_summary=criteria_summary,
        )
        yield f"event: complete\ndata: {json.dumps(complete.model_dump())}\n\n"

    async def _process_single_batch(
        self,
        semaphore: asyncio.Semaphore,
        batch_index: int,
        batch: list[dict],
        context: dict,
        session: "QuestionnaireSession",
        *,
        maturity_level: str,
        question_depth: str,
        priority_domains: list[str],
        compliance_concerns: str | None,
        controls_to_skip: str | None,
        on_progress: Any | None = None,
    ) -> list[ControlQuestions]:
        """Process a single batch of controls under semaphore concurrency."""
        async with semaphore:
            batch_num = batch_index + 1
            logger.info(f"Processing batch {batch_num} ({len(batch)} controls)")

            batch_controls_text = self._format_batch_controls(batch)

            batch_system_prompt = self._build_batch_system_prompt(
                context,
                batch_controls_text,
                maturity_level=maturity_level,
                question_depth=question_depth,
                priority_domains=priority_domains,
                compliance_concerns=compliance_concerns,
                controls_to_skip=controls_to_skip,
            )

            response = await self._client.messages.create(
                model=self._model,
                max_tokens=CRITERIA_MAX_TOKENS,
                system=batch_system_prompt,
                messages=[
                    {"role": "user", "content": "Generate the compliance assessment questions for these specific controls."}
                ],
            )

            text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text += block.text

            batch_controls = self._parse_questions(text, session.session_id)
            logger.info(f"Batch {batch_num} complete: {len(batch_controls)} controls, {sum(len(c.questions) for c in batch_controls)} questions")

            if on_progress:
                on_progress(batch_index, len(batch_controls))

            return batch_controls

    def _build_batch_system_prompt(
        self,
        context: dict,
        batch_controls_text: str,
        *,
        maturity_level: str,
        question_depth: str,
        priority_domains: list[str],
        compliance_concerns: str | None,
        controls_to_skip: str | None,
        questions_per_control: int | None = None,
    ) -> str:
        """Build system prompt for a specific batch of controls."""
        org_name = context.get("organization_name", "the organization")
        industry = context.get("industry", "unspecified")

        # Use explicit user choice if provided, otherwise fall back to depth_map
        if questions_per_control:
            q_count = f"{questions_per_control} questions per control"
        else:
            depth_map = {
                "high_level_overview": "2 questions per control",
                "balanced": "3 questions per control",
                "detailed_technical": "4-5 questions per control",
            }
            q_count = depth_map.get(question_depth, "3 questions per control")

        # Map maturity to complexity guidance
        maturity_map = {
            "first_time_audit": (
                "Focus on policy existence, basic documentation, and foundational "
                "controls. Use straightforward language. Prioritize 'do you have' "
                "over 'how effective is' questions."
            ),
            "recurring_assessment": (
                "Focus on implementation effectiveness, monitoring, and evidence "
                "of ongoing compliance. Ask about metrics, review cycles, and "
                "continuous improvement."
            ),
            "mature_isms": (
                "Focus on advanced effectiveness, optimization, and continuous "
                "improvement. Ask about benchmarking, automation, integration "
                "with business processes, and proactive threat management."
            ),
        }
        maturity_guidance = maturity_map.get(
            maturity_level, maturity_map["recurring_assessment"]
        )

        # Priority domains section
        priority_section = ""
        if priority_domains:
            priority_section = (
                f"\n\n## Priority Focus Areas\n"
                f"Generate MORE detailed and in-depth questions for these domains: "
                f"{', '.join(priority_domains)}. "
                f"For other domains, still generate questions but at standard depth."
            )

        # Compliance concerns section
        concerns_section = ""
        if compliance_concerns:
            concerns_section = (
                f"\n\n## Specific Compliance Concerns\n"
                f"The organization has flagged these concerns: {compliance_concerns}\n"
                f"Incorporate targeted questions that address these specific gaps "
                f"within relevant controls."
            )

        # Controls to skip
        skip_section = ""
        if controls_to_skip:
            skip_section = (
                f"\n\n## Controls to De-emphasize\n"
                f"Reduce coverage for: {controls_to_skip}. "
                f"Generate only 1 basic question for these controls."
            )

        return f"""You are a Senior ISMS Compliance Consultant & Auditor.
Organization: {org_name} ({industry})

## Controls to Process
{batch_controls_text}

## Assessment Criteria
Maturity Level: {maturity_level.replace('_', ' ').title()}
Question Depth: {q_count}
Complexity Guidance: {maturity_guidance}{priority_section}{concerns_section}{skip_section}

## Instructions
Generate questions for the specific controls listed above. Output ONLY a JSON array with this schema:
[
  {{
    "control_id": "ID",
    "control_title": "Title",
    "framework": "Framework Name",
    "questions": [
      {{
        "id": "q-<unique-id>",
        "question": "The question text",
        "category": "policy_existence|implementation|monitoring|effectiveness|documentation",
        "priority": "high|medium|low",
        "expected_evidence": "Expected evidence",
        "guidance_notes": "Guidance notes"
      }}
    ]
  }}
]

Ensure questions are specific to {org_name}'s context."""

    @retry(
        retry=retry_if_exception_type(
            (anthropic.RateLimitError, anthropic.APITimeoutError)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _call_criteria_generation(
        self, session: QuestionnaireSession
    ) -> anthropic.types.Message:
        """Call Claude without tools for direct question generation."""
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=CRITERIA_MAX_TOKENS,
            system=session.system_prompt,
            messages=session.messages,
        )
        logger.info(
            f"Session {session.session_id}: stop_reason={response.stop_reason}, "
            f"output_tokens={response.usage.output_tokens}"
        )
        session.messages.append(
            {"role": "assistant", "content": response.content}
        )
        return response

    async def continue_session(
        self, session_id: str, answer: str
    ) -> QuestionnaireResponse:
        """Continue a session by feeding the user's answer back to Claude.

        The answer is wrapped as a ``tool_result`` for the pending
        ``askQuestionToMe`` tool call.
        """
        session = _sessions.get(session_id)
        if session is None:
            session = await self._load_session_from_db(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found or expired")
        if session.status != "active":
            raise ValueError(f"Session {session_id} is already {session.status}")
        if session.pending_tool_use_id is None:
            raise ValueError("No pending question to answer")

        # Append the tool_result message
        session.messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": session.pending_tool_use_id,
                        "content": answer,
                    }
                ],
            }
        )
        session.pending_tool_use_id = None

        return await self._call_agent(session)

    # ------------------------------------------------------------------
    # Context fetching (parallel)
    # ------------------------------------------------------------------

    async def _fetch_cached_controls(self, table_name: str, sb: Any) -> list:
        """Fetch framework controls with TTL caching to avoid repeated full-table scans."""
        now = time.time()
        if table_name in _controls_cache:
            cached_at, data = _controls_cache[table_name]
            if now - cached_at < CONTROLS_CACHE_TTL:
                logger.debug(f"Cache hit for {table_name} ({len(data)} rows)")
                return data

        try:
            result = await sb.table(table_name).select("*").execute()
            data = result.data or []
            _controls_cache[table_name] = (now, data)
            logger.info(f"Cached {len(data)} rows from {table_name}")
            return data
        except Exception as e:
            logger.warning(f"Failed to fetch {table_name}: {e}")
            # Return stale cache if available
            if table_name in _controls_cache:
                _, data = _controls_cache[table_name]
                return data
            return []

    async def _fetch_project_context(self, project_id: str) -> dict:
        """Fetch all context needed for question generation in parallel."""
        from app.db.supabase import get_async_supabase_client_async

        sb = await get_async_supabase_client_async()

        # Phase 1: Fetch project + project-scoped data in parallel
        (
            project_res,
            findings_res,
            crawl_res,
        ) = await asyncio.gather(
            sb.table("projects").select("*").eq("id", project_id).execute(),
            sb.table("gap_analysis_findings")
            .select("*")
            .eq("project_id", project_id)
            .execute(),
            sb.table("web_crawl_results")
            .select("*")
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute(),
            return_exceptions=True,
        )

        context: dict[str, Any] = {"project_id": project_id}

        # Project
        if not isinstance(project_res, Exception) and project_res.data:
            project = project_res.data[0]
            context["project_name"] = project.get("name", "")
            context["client_id"] = project.get("client_id", "")
            raw = project.get("framework") or []
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except (ValueError, TypeError):
                    raw = [raw] if raw else []
            context["selected_frameworks"] = raw if isinstance(raw, list) else []
        else:
            context["client_id"] = ""
            context["selected_frameworks"] = []

        frameworks = context["selected_frameworks"]

        # Phase 2: Fetch client info (fresh) + framework controls (cached)
        client_id = context.get("client_id", "")
        if client_id:
            try:
                client_res = await sb.table("clients").select("*").eq("id", client_id).execute()
                if client_res.data:
                    client = client_res.data[0]
                    context["organization_name"] = client.get("name", "")
                    context["industry"] = client.get("industry", "")
            except Exception as e:
                logger.warning(f"Failed to fetch client info: {e}")

        # Findings
        if not isinstance(findings_res, Exception) and findings_res.data:
            context["findings"] = findings_res.data
        else:
            context["findings"] = []

        # Web crawl results
        if not isinstance(crawl_res, Exception) and crawl_res.data:
            crawl = crawl_res.data[0]
            context["business_context"] = crawl.get("business_context", {})
            context["digital_assets"] = crawl.get("digital_assets", [])
        else:
            context["business_context"] = {}
            context["digital_assets"] = []

        # Framework controls (cached — these rarely change)
        if not frameworks or "ISO 27001:2022" in frameworks:
            context["iso_controls"] = await self._fetch_cached_controls("iso_requirements", sb)
        else:
            context["iso_controls"] = []

        if not frameworks or "BNM RMIT" in frameworks:
            context["bnm_controls"] = await self._fetch_cached_controls("bnm_rmit_requirements", sb)
        else:
            context["bnm_controls"] = []

        # Document metadata from Supabase (optional, non-blocking)
        try:
            docs_res = (
                await sb.table("project_documents")
                .select("filename, format, word_count")
                .eq("project_id", project_id)
                .execute()
            )
            if docs_res.data:
                context["project_documents"] = docs_res.data
        except Exception as e:
            logger.warning(f"Document metadata fetch failed (non-critical): {e}")

        # Document chunks via pgvector (optional, non-blocking)
        try:
            from app.services.supabase_vector_service import get_supabase_vector_service

            vector_svc = get_supabase_vector_service()
            chunks = await vector_svc.search_client_extractions(
                client_id=client_id,
                query="compliance policy information security",
                limit=10,
            )
            context["document_chunks"] = chunks
        except Exception as e:
            logger.warning(f"pgvector search failed (non-critical): {e}")

        return context

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def _build_system_prompt(self, context: dict) -> str:
        """Build the agent system prompt with role, context, and instructions."""
        org_name = context.get("organization_name", "the organization")
        industry = context.get("industry", "unspecified")
        frameworks = context.get("selected_frameworks", [])
        business_ctx = context.get("business_context", {})
        findings = context.get("findings", [])

        # Summarise documents from project_documents context
        docs = context.get("project_documents", [])
        doc_names = [d.get("filename", "unknown") for d in docs if d]

        # Build framework controls section
        controls_text = self._format_controls(context)

        # Business context summary
        biz_summary = ""
        if business_ctx:
            biz_summary = json.dumps(business_ctx, default=str)[:2000]

        # Findings summary
        findings_summary = f"{len(findings)} existing findings" if findings else "No existing findings"

        scope_stmt = context.get("scope_statement_isms", "")

        return f"""You are a Senior ISMS Compliance Consultant & Auditor.

Goal: Generate targeted, actionable compliance assessment questions specific to the organization's context, industry, and regulatory landscape.

Backstory: You have 15+ years of experience conducting compliance audits for financial institutions across Southeast Asia, specializing in {' and '.join(frameworks) if frameworks else 'BNM RMIT and ISO 27001:2022'}. You understand that generic questionnaires produce generic results — the best assessments are tailored to the organization's specific risks, maturity, and operational context.

## Project Context
Organization: {org_name} ({industry})
Frameworks: {', '.join(frameworks) if frameworks else 'Not specified'}
Business Context: {biz_summary or 'Not available'}
ISMS Scope: {scope_stmt or 'Not specified'}
Documents Uploaded: {len(doc_names)} ({', '.join(doc_names[:10]) if doc_names else 'none'})
Existing Findings: {findings_summary}

## Framework Controls
{controls_text}

## Instructions
1. Use the askQuestionToMe tool to understand the user's criteria. Key areas:
   - **Questions per control (REQUIRED)**: You MUST ask the user how many questions they want generated per control. Present these options: 2 (high-level overview), 3 (balanced), or 4-5 (detailed technical). This is a required question — do not skip it.
   - Priority focus areas (which control domains matter most)
   - Specific compliance concerns or known gaps
   - Assessment maturity level (first-time vs recurring audit)
   - Any controls to skip or emphasize
2. Ask 2-4 clarifying questions total, one at a time. The questions-per-control question should be one of them.
3. Once you have enough context, call the generateQuestionnaire tool with the criteria you've gathered, including the questions_per_control value. Do NOT output questions directly — the system will generate them in optimized batches.

IMPORTANT: Always end the conversation by calling generateQuestionnaire. Never try to output a JSON array of questions yourself."""

    def _format_controls(self, context: dict) -> str:
        """Format framework controls for the system prompt."""
        parts = []
        frameworks = context.get("selected_frameworks", [])

        if not frameworks or "ISO 27001:2022" in frameworks:
            iso_controls = context.get("iso_controls", [])
            if iso_controls:
                parts.append("### ISO 27001:2022 Controls")
                for c in iso_controls[:100]:  # Hard limit to 100 to avoid overflow
                    identifier = c.get("identifier", "")
                    title = c.get("title", "")
                    desc = c.get("description", "")[:150]
                    parts.append(f"- **{identifier}**: {title} — {desc}")

        if not frameworks or "BNM RMIT" in frameworks:
            bnm_controls = context.get("bnm_controls", [])
            if bnm_controls:
                parts.append("\n### BNM RMIT Controls")
                for c in bnm_controls[:100]: # Hard limit to 100
                    ref = c.get("reference_id", "")
                    title = c.get("subsection_title") or c.get("section_title", "")
                    desc = c.get("requirement_text", "")[:150]
                    parts.append(f"- **{ref}**: {title} — {desc}")

        return "\n".join(parts) if parts else "No framework controls loaded."

    def _build_criteria_system_prompt(
        self,
        context: dict,
        *,
        maturity_level: str,
        question_depth: str,
        priority_domains: list[str],
        compliance_concerns: str | None,
        controls_to_skip: str | None,
        questions_per_control: int | None = None,
    ) -> str:
        """Build system prompt with structured criteria baked in."""
        org_name = context.get("organization_name", "the organization")
        industry = context.get("industry", "unspecified")
        frameworks = context.get("selected_frameworks", [])
        business_ctx = context.get("business_context", {})
        findings = context.get("findings", [])
        docs = context.get("project_documents", [])
        doc_names = [d.get("filename", "unknown") for d in docs if d]
        controls_text = self._format_controls(context)
        biz_summary = ""
        if business_ctx:
            biz_summary = json.dumps(business_ctx, default=str)[:2000]
        findings_summary = (
            f"{len(findings)} existing findings" if findings else "No existing findings"
        )
        scope_stmt = context.get("scope_statement_isms", "")

        # Use explicit user choice if provided, otherwise fall back to depth_map
        if questions_per_control:
            q_count = f"{questions_per_control} questions per control"
        else:
            depth_map = {
                "high_level_overview": "2 questions per control",
                "balanced": "3 questions per control",
                "detailed_technical": "4-5 questions per control",
            }
            q_count = depth_map.get(question_depth, "3 questions per control")

        # Map maturity to complexity guidance
        maturity_map = {
            "first_time_audit": (
                "Focus on policy existence, basic documentation, and foundational "
                "controls. Use straightforward language. Prioritize 'do you have' "
                "over 'how effective is' questions."
            ),
            "recurring_assessment": (
                "Focus on implementation effectiveness, monitoring, and evidence "
                "of ongoing compliance. Ask about metrics, review cycles, and "
                "continuous improvement."
            ),
            "mature_isms": (
                "Focus on advanced effectiveness, optimization, and continuous "
                "improvement. Ask about benchmarking, automation, integration "
                "with business processes, and proactive threat management."
            ),
        }
        maturity_guidance = maturity_map.get(maturity_level, maturity_map["recurring_assessment"])

        # Priority domains section
        priority_section = ""
        if priority_domains:
            priority_section = (
                f"\n\n## Priority Focus Areas\n"
                f"Generate MORE detailed and in-depth questions for these domains: "
                f"{', '.join(priority_domains)}. "
                f"For other domains, still generate questions but at standard depth."
            )

        # Compliance concerns section
        concerns_section = ""
        if compliance_concerns:
            concerns_section = (
                f"\n\n## Specific Compliance Concerns\n"
                f"The organization has flagged these concerns: {compliance_concerns}\n"
                f"Incorporate targeted questions that address these specific gaps "
                f"within relevant controls."
            )

        # Controls to skip
        skip_section = ""
        if controls_to_skip:
            skip_section = (
                f"\n\n## Controls to De-emphasize\n"
                f"Reduce coverage for: {controls_to_skip}. "
                f"Generate only 1 basic question for these controls."
            )

        return f"""You are a Senior ISMS Compliance Consultant & Auditor.

Goal: Generate targeted, actionable compliance assessment questions specific to the organization's context, industry, and regulatory landscape.

Backstory: You have 15+ years of experience conducting compliance audits for financial institutions across Southeast Asia, specializing in {' and '.join(frameworks) if frameworks else 'BNM RMIT and ISO 27001:2022'}. You understand that generic questionnaires produce generic results — the best assessments are tailored to the organization's specific risks, maturity, and operational context.

## Project Context
Organization: {org_name} ({industry})
Frameworks: {', '.join(frameworks) if frameworks else 'Not specified'}
Business Context: {biz_summary or 'Not available'}
ISMS Scope: {scope_stmt or 'Not specified'}
Documents Uploaded: {len(doc_names)} ({', '.join(doc_names[:10]) if doc_names else 'none'})
Existing Findings: {findings_summary}

## Framework Controls
{controls_text}

## Assessment Criteria
Maturity Level: {maturity_level.replace('_', ' ').title()}
Question Depth: {q_count}
Complexity Guidance: {maturity_guidance}{priority_section}{concerns_section}{skip_section}

## Instructions
Generate questions for EVERY control in the selected frameworks. Output ONLY a JSON array with this exact schema (no prose, no markdown fences, no explanation):

[
  {{
    "control_id": "Control ID from the list",
    "control_title": "Control title from the list",
    "framework": "The framework this control belongs to (e.g. ISO 27001:2022 or BNM RMIT)",
    "questions": [
      {{
        "id": "q-<unique-id>",
        "question": "The assessment question text",
        "category": "policy_existence|implementation|monitoring|effectiveness|documentation",
        "priority": "high|medium|low",
        "expected_evidence": "What evidence the assessor should look for",
        "guidance_notes": "Hints for the assessor on evaluating the answer"
      }}
    ]
  }}
]

IMPORTANT: Set the "framework" field to match the actual framework each control belongs to (e.g. "BNM RMIT" for BNM controls, "ISO 27001:2022" for ISO controls).

Generate {q_count} depending on the criteria above. Ensure questions are specific to {org_name}'s context, not generic boilerplate."""

    @staticmethod
    def _build_criteria_summary(
        *,
        maturity_level: str,
        question_depth: str,
        priority_domains: list[str],
        compliance_concerns: str | None,
        controls_to_skip: str | None,
        questions_per_control: int | None = None,
    ) -> str:
        """Build a human-readable criteria summary from structured inputs."""
        maturity_labels = {
            "first_time_audit": "First-time audit",
            "recurring_assessment": "Recurring assessment",
            "mature_isms": "Mature ISMS",
        }
        depth_labels = {
            "high_level_overview": "High-level overview (2 Q/control)",
            "balanced": "Balanced (3 Q/control)",
            "detailed_technical": "Detailed technical (4-5 Q/control)",
        }

        parts = [
            f"Maturity: {maturity_labels.get(maturity_level, maturity_level)}",
            f"Depth: {depth_labels.get(question_depth, question_depth)}",
        ]
        if questions_per_control:
            parts.append(f"Questions/control: {questions_per_control}")
        if priority_domains:
            parts.append(f"Priority domains: {', '.join(priority_domains)}")
        if compliance_concerns:
            parts.append(f"Concerns: {compliance_concerns}")
        if controls_to_skip:
            parts.append(f"De-emphasized: {controls_to_skip}")

        return "; ".join(parts)

    @staticmethod
    def _filter_controls(
        controls: list[dict], priority_domains: list[str]
    ) -> list[dict]:
        """Filter controls to only those matching the given priority domains.

        ISO 27001 matching:
          - "A.7 Physical Controls" → prefix "A.7" matches control identifiers
          - "Clauses 4-10 (Management)" → matches single-digit identifiers 4–10

        BNM RMIT matching:
          - Substring containment between domain label and section_title
            (handles label mismatches like "Risk Management" ↔ "Technology Risk Management")
        """
        iso_prefixes: list[str] = []
        include_management_clauses = False
        bnm_labels: list[str] = []

        for domain in priority_domains:
            # Check for ISO Annex A prefix pattern like "A.5", "A.7"
            m = re.match(r"^(A\.\d+)", domain)
            if m:
                iso_prefixes.append(m.group(1))
            elif "clauses 4-10" in domain.lower() or "clauses 4–10" in domain.lower():
                include_management_clauses = True
            else:
                # Treat as BNM RMIT domain label
                bnm_labels.append(domain.lower())

        def _matches(ctrl: dict) -> bool:
            fw = ctrl.get("framework", "")

            if fw == "ISO 27001:2022":
                ctrl_domain = ctrl.get("domain", "")
                # Annex A prefix match
                if iso_prefixes and ctrl_domain in iso_prefixes:
                    return True
                # Management clauses (identifiers like "4", "5", ... "10")
                if include_management_clauses and ctrl_domain.isdigit():
                    num = int(ctrl_domain)
                    if 4 <= num <= 10:
                        return True
                return False

            if fw == "BNM RMIT":
                section = ctrl.get("section_title", "").lower()
                section_num = ctrl.get("section_number")
                for label in bnm_labels:
                    # Bidirectional substring: "risk management" in
                    # "technology risk management" OR vice versa
                    if label in section or section in label:
                        return True
                    # Numeric matching: "Sections 8-9" or "Section 8"
                    if section_num is not None:
                        nums = re.findall(r'\d+', label)
                        if str(section_num) in nums:
                            return True
                return False

            return False

        return [c for c in controls if _matches(c)]

    # ------------------------------------------------------------------
    # Claude API interaction
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type(
            (anthropic.RateLimitError, anthropic.APITimeoutError)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _call_agent(
        self, session: QuestionnaireSession
    ) -> QuestionnaireResponse:
        """Call Claude and handle tool_use vs end_turn."""
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            system=session.system_prompt,
            messages=session.messages,
            tools=TOOLS,
        )

        # Append assistant response to conversation history
        session.messages.append(
            {"role": "assistant", "content": response.content}
        )

        # Check if Claude wants to use a tool
        if response.stop_reason == "tool_use":
            tool_block = next(
                (b for b in response.content if b.type == "tool_use"), None
            )
            if tool_block and tool_block.name == "askQuestionToMe":
                session.pending_tool_use_id = tool_block.id

                # Persist active state so session survives restarts
                await self._persist_active_session(session)

                return AgentQuestion(
                    session_id=session.session_id,
                    question=tool_block.input.get("question", ""),
                    context=tool_block.input.get("context"),
                    options=tool_block.input.get("options"),
                )

            if tool_block and tool_block.name == "generateQuestionnaire":
                # Extract criteria from tool input and run batch generation
                criteria = tool_block.input
                logger.info(
                    f"Session {session.session_id}: agent called generateQuestionnaire, "
                    f"starting batch generation with criteria: {criteria}"
                )
                return await self._run_batch_generation(session, criteria)

        # If it's not a tool use, check if it contains JSON questions
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text
        
        if "[" in text and "]" in text and "control_id" in text:
            # end_turn — agent is done, extract generated questions
            return await self._handle_completion(session, response)
        
        # Fallback: if it's just text, treat it as a question to the user
        # but without tool metadata (manual fallback)
        await self._persist_active_session(session)
        return AgentQuestion(
            session_id=session.session_id,
            question=text.strip() or "I need more information to generate the questions. Could you please clarify your requirements?",
            context="The agent provided a text response instead of using a tool or generating JSON."
        )

    # ------------------------------------------------------------------
    # Batch generation from conversational criteria
    # ------------------------------------------------------------------

    def _build_controls_list(self, context: dict) -> list[dict]:
        """Build a unified controls list from project context.

        Shared by both ``generate_with_criteria`` (wizard flow) and
        ``_run_batch_generation`` (conversational flow).
        """
        iso_controls = context.get("iso_controls", [])
        bnm_controls = context.get("bnm_controls", [])

        all_controls: list[dict] = []
        for c in iso_controls:
            identifier = c.get("identifier", "")
            parts = identifier.split(".")
            if len(parts) >= 2 and parts[0] == "A":
                domain = f"A.{parts[1]}"
            else:
                domain = identifier.split(".")[0] if identifier else ""
            all_controls.append({
                "id": identifier,
                "title": c.get("title"),
                "framework": "ISO 27001:2022",
                "desc": c.get("description", "")[:200],
                "domain": domain,
            })
        for c in bnm_controls:
            all_controls.append({
                "id": c.get("reference_id"),
                "title": c.get("subsection_title") or c.get("section_title", ""),
                "framework": "BNM RMIT",
                "desc": c.get("requirement_text", "")[:200],
                "section_title": c.get("section_title", ""),
                "section_number": c.get("section_number"),
            })
        return all_controls

    @staticmethod
    def _format_batch_controls(batch: list[dict]) -> str:
        """Format a batch of controls into text for the batch system prompt."""
        return _fmt_controls(batch)

    async def _run_batch_generation(
        self,
        session: QuestionnaireSession,
        criteria: dict,
    ) -> QuestionnaireComplete:
        """Run batch question generation using criteria from the conversation."""
        context = session.project_context
        maturity_level = criteria.get("maturity_level", "developing")
        question_depth = criteria.get("question_depth", "balanced")
        priority_domains = criteria.get("priority_domains") or []
        compliance_concerns = criteria.get("compliance_concerns")
        criteria_summary = criteria.get("criteria_summary", "")
        questions_per_control = criteria.get("questions_per_control")

        all_controls = self._build_controls_list(context)

        if priority_domains:
            all_controls = self._filter_controls(all_controls, priority_domains)
            logger.info(
                f"Filtered to {len(all_controls)} controls for priority domains: "
                f"{priority_domains}"
            )

        if not all_controls:
            session.status = "completed"
            elapsed_ms = int(time.time() * 1000) - session.started_at_ms
            return QuestionnaireComplete(
                session_id=session.session_id,
                controls=[],
                total_controls=0,
                total_questions=0,
                generation_time_ms=elapsed_ms,
                criteria_summary=criteria_summary,
            )

        # Use swarm for parallel generation (replaces sequential batch loop)
        criteria_dict = {
            "maturity_level": maturity_level,
            "question_depth": question_depth,
            "priority_domains": priority_domains,
            "compliance_concerns": compliance_concerns,
            "questions_per_control": questions_per_control,
        }
        swarm_result = await self._swarm.generate(
            all_controls, context, criteria_dict, session.session_id
        )
        all_generated = swarm_result.controls

        total_q = sum(len(c.questions) for c in all_generated)
        elapsed_ms = int(time.time() * 1000) - session.started_at_ms
        session.status = "completed"

        await self._persist_results(
            session, all_generated, total_q, elapsed_ms, criteria_summary
        )

        return QuestionnaireComplete(
            session_id=session.session_id,
            controls=all_generated,
            total_controls=len(all_generated),
            total_questions=total_q,
            generation_time_ms=elapsed_ms,
            criteria_summary=criteria_summary,
        )

    async def _handle_completion(
        self,
        session: QuestionnaireSession,
        response: anthropic.types.Message,
        criteria_summary_override: str | None = None,
    ) -> QuestionnaireComplete:
        """Parse final response and persist results."""
        elapsed_ms = int(time.time() * 1000) - session.started_at_ms
        session.status = "completed"

        # Extract text from response
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        controls = self._parse_questions(text, session.session_id)
        total_questions = sum(len(c.questions) for c in controls)

        # Use override (wizard flow) or extract from conversation (chat flow)
        criteria_summary = (
            criteria_summary_override
            if criteria_summary_override is not None
            else self._extract_criteria_summary(session)
        )

        # Persist to Supabase
        await self._persist_results(
            session, controls, total_questions, elapsed_ms, criteria_summary
        )

        return QuestionnaireComplete(
            session_id=session.session_id,
            controls=controls,
            total_controls=len(controls),
            total_questions=total_questions,
            generation_time_ms=elapsed_ms,
            criteria_summary=criteria_summary,
        )

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_questions(
        self, text: str, session_id: str
    ) -> list[ControlQuestions]:
        """Extract JSON questions array from Claude's final response."""
        return parse_questions(text, session_id)

    @staticmethod
    def _extract_json_array(text: str) -> Optional[str]:
        """Find the outermost JSON array in a text blob."""
        return extract_json_array(text)

    def _extract_criteria_summary(self, session: QuestionnaireSession) -> str:
        """Build a summary of the user's stated criteria from the conversation."""
        user_answers = []
        for msg in session.messages:
            if msg["role"] != "user":
                continue
            content = msg.get("content", "")
            if isinstance(content, str):
                if content.startswith("I'd like to generate"):
                    continue
                user_answers.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        user_answers.append(block.get("content", ""))

        if not user_answers:
            return "No specific criteria provided"

        return "; ".join(user_answers)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def _get_existing_session(self, assessment_id: str) -> QuestionnaireComplete | None:
        """Return a cached QuestionnaireComplete if a completed session exists for this assessment."""
        try:
            from app.db.supabase import get_async_supabase_client_async

            sb = await get_async_supabase_client_async()
            result = (
                await sb.table("questionnaire_sessions")
                .select("id, generated_questions, total_controls, total_questions, generation_time_ms, agent_criteria")
                .eq("assessment_id", assessment_id)
                .eq("status", "completed")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            if not result.data:
                return None

            row = result.data[0]
            controls = [ControlQuestions(**c) for c in row["generated_questions"]]
            return QuestionnaireComplete(
                session_id=row["id"],
                controls=controls,
                total_controls=row["total_controls"],
                total_questions=row["total_questions"],
                generation_time_ms=row["generation_time_ms"],
                criteria_summary=row.get("agent_criteria", {}).get("summary", ""),
            )
        except Exception as e:
            logger.warning(f"Cache lookup failed for assessment {assessment_id}: {e}")
            return None

    @staticmethod
    def _serialize_messages(messages: list[dict]) -> list[dict]:
        """Serialize conversation messages for JSONB storage.

        Handles Anthropic content blocks (which have ``.model_dump()``) as well
        as plain dicts and strings.
        """
        conversation: list[dict] = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                serialized = []
                for block in content:
                    if hasattr(block, "model_dump"):
                        serialized.append(block.model_dump())
                    elif isinstance(block, dict):
                        serialized.append(block)
                    else:
                        serialized.append(str(block))
                conversation.append(
                    {"role": msg["role"], "content": serialized}
                )
            else:
                conversation.append(msg)
        return conversation

    # ------------------------------------------------------------------
    # Active session persistence (survives restarts)
    # ------------------------------------------------------------------

    async def _persist_active_session(
        self, session: QuestionnaireSession
    ) -> None:
        """Upsert the active session state to Supabase so it survives restarts."""
        try:
            from app.db.supabase import get_async_supabase_client_async

            sb = await get_async_supabase_client_async()
            conversation = self._serialize_messages(session.messages)

            row: dict[str, Any] = {
                "id": session.session_id,
                "project_id": session.project_id,
                "client_id": session.client_id,
                "user_id": session.user_id,
                "status": "active",
                "conversation_history": conversation,
                "pending_tool_use_id": session.pending_tool_use_id,
                "started_at_ms": session.started_at_ms,
                "model_used": self._model,
                "created_by": session.user_id,
            }
            if session.assessment_id:
                row["assessment_id"] = session.assessment_id

            await sb.table("questionnaire_sessions").upsert(row).execute()

            logger.debug(
                f"Session {session.session_id}: persisted active state "
                f"({len(session.messages)} messages)"
            )
        except Exception as e:
            logger.error(
                f"Session {session.session_id}: failed to persist active state: {e}"
            )

    async def _load_session_from_db(
        self, session_id: str
    ) -> QuestionnaireSession | None:
        """Load an active session from DB when not found in memory.

        This is the key method that enables session recovery after a backend
        restart.  It re-fetches project context, rebuilds the system prompt,
        and deserializes the conversation history.
        """
        try:
            from app.db.supabase import get_async_supabase_client_async

            sb = await get_async_supabase_client_async()
            result = (
                await sb.table("questionnaire_sessions")
                .select("*")
                .eq("id", session_id)
                .eq("status", "active")
                .limit(1)
                .execute()
            )

            if not result.data:
                return None

            row = result.data[0]
            project_id = row["project_id"]

            # Re-fetch context and rebuild system prompt (not stored in DB)
            context = await self._fetch_project_context(project_id)
            system_prompt = self._build_system_prompt(context)

            messages = row.get("conversation_history") or []

            session = QuestionnaireSession(
                session_id=session_id,
                project_id=project_id,
                client_id=row["client_id"],
                user_id=row["user_id"],
                assessment_id=row.get("assessment_id"),
                messages=messages,
                pending_tool_use_id=row.get("pending_tool_use_id"),
                project_context=context,
                system_prompt=system_prompt,
                started_at_ms=row.get("started_at_ms") or 0,
                status="active",
            )

            # Re-cache in memory
            _sessions[session_id] = session
            logger.info(
                f"Session {session_id}: restored from DB "
                f"({len(messages)} messages)"
            )
            return session

        except Exception as e:
            logger.error(f"Failed to load session {session_id} from DB: {e}")
            return None

    # ------------------------------------------------------------------
    # Completed session persistence
    # ------------------------------------------------------------------

    async def _persist_results(
        self,
        session: QuestionnaireSession,
        controls: list[ControlQuestions],
        total_questions: int,
        elapsed_ms: int,
        criteria_summary: str,
    ) -> None:
        """Store completed questionnaire session to Supabase."""
        try:
            from app.db.supabase import get_async_supabase_client_async

            sb = await get_async_supabase_client_async()

            controls_json = [c.model_dump() for c in controls]
            conversation = self._serialize_messages(session.messages)

            row: dict[str, Any] = {
                "id": session.session_id,
                "project_id": session.project_id,
                "client_id": session.client_id,
                "user_id": session.user_id,
                "status": "completed",
                "agent_criteria": {"summary": criteria_summary},
                "generated_questions": controls_json,
                "conversation_history": conversation,
                "model_used": self._model,
                "total_controls": len(controls),
                "total_questions": total_questions,
                "generation_time_ms": elapsed_ms,
                "completed_at": datetime.utcnow().isoformat(),
                "created_by": session.user_id,
                "pending_tool_use_id": None,
            }
            if session.assessment_id:
                row["assessment_id"] = session.assessment_id

            # Use upsert: the row may already exist from active session persistence
            await sb.table("questionnaire_sessions").upsert(row).execute()

            logger.info(
                f"Session {session.session_id}: persisted {total_questions} "
                f"questions across {len(controls)} controls"
            )
        except Exception as e:
            logger.error(
                f"Session {session.session_id}: failed to persist results: {e}"
            )
