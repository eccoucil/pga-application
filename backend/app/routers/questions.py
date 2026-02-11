"""Questions router for contextual question generation and review."""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.services.context_aggregator import get_context_aggregator
from app.services.question_generator import (
    ControlDefinition,
    ControlQuestionSet,
    get_question_generator,
)

router = APIRouter(prefix="/questions", tags=["questions"])


class GenerateRequest(BaseModel):
    """Request to generate questions for a framework."""

    project_id: str
    client_id: str
    framework: str = Field("iso_27001", description="Framework: iso_27001 or bnm_rmit")


class GenerateResponse(BaseModel):
    """Response from question generation."""

    batch_id: str
    question_count: int
    sections_processed: int
    status: str = "pending_review"
    control_sets: list[ControlQuestionSet] = Field(default_factory=list)


class QuestionReviewItem(BaseModel):
    """Question item for review."""

    id: str
    control_id: str
    control_title: str
    questions: list[dict]
    status: str
    priority: str
    batch_id: str
    generated_at: datetime


class PendingQuestionsResponse(BaseModel):
    """Response with pending questions for review."""

    project_id: str
    total_pending: int
    questions: list[QuestionReviewItem]


class ApproveRequest(BaseModel):
    """Request to approve a question set."""

    review_notes: Optional[str] = None


class EditRequest(BaseModel):
    """Request to edit and approve a question set."""

    questions: list[dict] = Field(..., description="Modified questions array")
    review_notes: Optional[str] = None


class RejectRequest(BaseModel):
    """Request to reject a question set."""

    reason: str = Field(..., min_length=10, description="Reason for rejection")
    regenerate: bool = Field(False, description="Whether to trigger regeneration")


# Section title mappings
ISO_SECTION_TITLES = {
    "4": "Context of the Organization",
    "5": "Leadership",
    "6": "Planning",
    "7": "Support",
    "8": "Operation",
    "9": "Performance Evaluation",
    "10": "Improvement",
    "A.5": "Organizational Controls",
    "A.6": "People Controls",
    "A.7": "Physical Controls",
    "A.8": "Technological Controls",
}

BNM_SECTION_TITLES = {
    "section_6": "Technology Risk Governance",
    "section_7": "Technology Operations Management",
    "section_8": "Cybersecurity Management",
    "section_9": "Technology Audit",
    "section_10": "Internal Awareness and Training",
    "section_11": "Technology Project Management",
    "section_12": "Cloud Services",
    "section_13": "Access Control",
    "section_14": "Data Management",
}

FRAMEWORK_SECTIONS: dict[str, list[str]] = {
    "iso_27001": list(ISO_SECTION_TITLES.keys()),
    "bnm_rmit": [f"section_{n}" for n in range(6, 15)],
}

# Maximum concurrent LLM calls for question generation
MAX_CONCURRENT_GENERATIONS = 10


def _get_section_title(framework: str, section_id: str) -> str:
    """Resolve a human-readable section title."""
    if framework == "iso_27001":
        return ISO_SECTION_TITLES.get(section_id, section_id)
    return BNM_SECTION_TITLES.get(section_id, section_id)


def _derive_section_id(framework: str, control: dict) -> str:
    """Derive the section_id from a raw control row."""
    if framework == "iso_27001":
        # Annex A controls have category_code like "A.5"
        if control.get("category_code"):
            return control["category_code"]
        # Management clauses: identifier like "4.1" → section "4"
        identifier = control.get("identifier", "")
        return identifier.split(".")[0] if "." in identifier else identifier
    # BNM RMIT: section_number → "section_N"
    return f"section_{control.get('section_number', '')}"


@router.post("/generate", response_model=GenerateResponse)
async def generate_questions(
    request: GenerateRequest,
    current_user: dict = Depends(get_current_user),
) -> GenerateResponse:
    """
    Generate contextual questions for all sections of a framework.

    This triggers on-demand question generation using:
    1. Organization context from Neo4j
    2. Web crawl data (digital assets, services)
    3. Document intelligence (controls referenced)
    4. Claude Opus 4.5 for generation

    Questions are stored with status='pending_review' for consultant approval.
    """
    settings = get_settings()

    from supabase import create_client

    supabase = create_client(settings.supabase_url, settings.supabase_service_key)

    sections = FRAMEWORK_SECTIONS.get(request.framework)
    if not sections:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown framework: {request.framework}",
        )

    # Build context once (section=None covers the whole framework)
    context_aggregator = get_context_aggregator()
    context = await context_aggregator.build_context(
        client_id=request.client_id,
        project_id=request.project_id,
        framework=request.framework,
    )

    generator = get_question_generator()
    batch_id = str(uuid4())

    # Phase 1: Collect all controls across sections (fast, sequential DB queries)
    all_controls: list[tuple[ControlDefinition, str, str]] = []
    for section in sections:
        if request.framework == "iso_27001":
            if section.startswith("A."):
                result = (
                    supabase.table("iso_requirements")
                    .select("*")
                    .eq("category_code", section)
                    .execute()
                )
            else:
                result = (
                    supabase.table("iso_requirements")
                    .select("*")
                    .eq("clause_type", "management")
                    .like("identifier", f"{section}%")
                    .execute()
                )
        else:
            section_num = section.replace("section_", "")
            result = (
                supabase.table("bnm_rmit_requirements")
                .select("*")
                .eq("section_number", int(section_num))
                .execute()
            )

        controls_data = result.data
        if not controls_data:
            logging.warning(f"No controls found for section {section}, skipping")
            continue

        section_id = _derive_section_id(request.framework, controls_data[0])
        section_title = _get_section_title(request.framework, section_id)

        for c in controls_data:
            if request.framework == "iso_27001":
                control = ControlDefinition(
                    identifier=c["identifier"],
                    title=c["title"],
                    description=c.get("description"),
                    category=c.get("category"),
                    key_activities=c.get("key_activities") or [],
                )
            else:
                control = ControlDefinition(
                    identifier=c["reference_id"],
                    title=c.get("subsection_title") or c["section_title"],
                    description=c.get("requirement_text"),
                    category=c.get("requirement_type"),
                    key_activities=[],
                )
            all_controls.append((control, section_id, section_title))

    if not all_controls:
        raise HTTPException(
            status_code=404,
            detail=f"No controls found for framework {request.framework}",
        )

    # Phase 2: Generate questions concurrently with bounded parallelism
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_GENERATIONS)

    async def _generate_one(
        control: ControlDefinition, section_id: str, section_title: str
    ) -> ControlQuestionSet:
        async with semaphore:
            question_set = await generator.generate_for_control(
                control=control,
                context=context,
                batch_id=batch_id,
            )
            await _store_questions(
                supabase=supabase,
                question_set=question_set,
                request=request,
                user_id=current_user["user_id"],
                section_id=section_id,
                section_title=section_title,
            )
            return question_set

    results = await asyncio.gather(
        *[_generate_one(ctrl, sid, stitle) for ctrl, sid, stitle in all_controls],
        return_exceptions=True,
    )

    # Phase 3: Collect results, log failures
    control_sets: list[ControlQuestionSet] = []
    failed = 0
    for (ctrl, _, _), result in zip(all_controls, results):
        if isinstance(result, Exception):
            logging.error(f"Failed to generate for {ctrl.identifier}: {result}")
            failed += 1
        else:
            control_sets.append(result)

    if failed:
        logging.warning(
            f"Question generation: {failed}/{len(all_controls)} controls failed"
        )

    sections_processed = len({sid for _, sid, _ in all_controls})

    if not control_sets:
        raise HTTPException(
            status_code=404,
            detail=f"No controls found for framework {request.framework}",
        )

    return GenerateResponse(
        batch_id=batch_id,
        question_count=sum(len(cs.questions) for cs in control_sets),
        sections_processed=sections_processed,
        status="pending_review",
        control_sets=control_sets,
    )


async def _store_questions(
    supabase,
    question_set: ControlQuestionSet,
    request: GenerateRequest,
    user_id: str,
    section_id: str,
    section_title: str,
) -> None:
    """Store generated questions in Supabase."""
    # Serialize questions to JSONB format
    questions_json = [
        {
            "question_number": q.question_number,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "expected_evidence": q.expected_evidence,
            "grounding_source": q.grounding_source,
            "context_source": q.context_source,
        }
        for q in question_set.questions
    ]

    supabase.table("framework_questions").insert(
        {
            "client_id": request.client_id,
            "project_id": request.project_id,
            "user_id": user_id,
            "framework": request.framework,
            "control_id": question_set.control_id,
            "control_title": question_set.control_title,
            "control_description": question_set.control_description,
            "questions": questions_json,
            "section_id": section_id,
            "section_title": section_title,
            "batch_id": question_set.batch_id,
            "priority": question_set.priority,
            "status": "pending_review",
            "context_source": {},  # Could be enriched with actual context used
        }
    ).execute()


@router.get("/{project_id}/pending", response_model=PendingQuestionsResponse)
async def get_pending_questions(
    project_id: str,
    section: Optional[str] = Query(None, description="Filter by section"),
    current_user: dict = Depends(get_current_user),
) -> PendingQuestionsResponse:
    """
    Get questions pending review for a project.

    Consultant uses this to review generated questions before
    they're shown to the client.
    """
    settings = get_settings()

    from supabase import create_client

    supabase = create_client(settings.supabase_url, settings.supabase_service_key)

    # Build query
    query = (
        supabase.table("framework_questions")
        .select("*")
        .eq("project_id", project_id)
        .eq("status", "pending_review")
    )

    if section:
        query = query.eq("section_id", section)

    result = query.order("created_at", desc=True).execute()

    questions = [
        QuestionReviewItem(
            id=q["id"],
            control_id=q["control_id"],
            control_title=q["control_title"],
            questions=q["questions"],
            status=q["status"],
            priority=q.get("priority", "medium"),
            batch_id=q.get("batch_id", ""),
            generated_at=q["generated_at"] or q["created_at"],
        )
        for q in result.data
    ]

    return PendingQuestionsResponse(
        project_id=project_id,
        total_pending=len(questions),
        questions=questions,
    )


@router.put("/{question_id}/approve")
async def approve_question(
    question_id: str,
    request: ApproveRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Approve a question set for client view.

    After approval, questions will be visible in the client questionnaire.
    """
    settings = get_settings()

    from supabase import create_client

    supabase = create_client(settings.supabase_url, settings.supabase_service_key)

    result = (
        supabase.table("framework_questions")
        .update(
            {
                "status": "approved",
                "reviewed_by": current_user["user_id"],
                "reviewed_at": datetime.utcnow().isoformat(),
                "review_notes": request.review_notes,
            }
        )
        .eq("id", question_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Question not found")

    return {"status": "approved", "question_id": question_id}


@router.put("/{question_id}/edit")
async def edit_question(
    question_id: str,
    request: EditRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Edit questions and approve.

    Allows consultant to modify questions before approving.
    """
    settings = get_settings()

    from supabase import create_client

    supabase = create_client(settings.supabase_url, settings.supabase_service_key)

    result = (
        supabase.table("framework_questions")
        .update(
            {
                "questions": request.questions,
                "status": "approved",
                "reviewed_by": current_user["user_id"],
                "reviewed_at": datetime.utcnow().isoformat(),
                "review_notes": request.review_notes,
                "updated_by": current_user["user_id"],
            }
        )
        .eq("id", question_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Question not found")

    return {"status": "approved", "question_id": question_id, "edited": True}


@router.put("/{question_id}/reject")
async def reject_question(
    question_id: str,
    request: RejectRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Reject a question set.

    Optionally triggers regeneration with the rejection reason as feedback.
    """
    settings = get_settings()

    from supabase import create_client

    supabase = create_client(settings.supabase_url, settings.supabase_service_key)

    new_status = "regenerating" if request.regenerate else "rejected"

    result = (
        supabase.table("framework_questions")
        .update(
            {
                "status": new_status,
                "reviewed_by": current_user["user_id"],
                "reviewed_at": datetime.utcnow().isoformat(),
                "review_notes": request.reason,
            }
        )
        .eq("id", question_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Question not found")

    # TODO: If regenerate=True, trigger async regeneration with feedback

    return {
        "status": new_status,
        "question_id": question_id,
        "regenerate_triggered": request.regenerate,
    }


@router.get("/{project_id}/approved")
async def get_approved_questions(
    project_id: str,
    section: Optional[str] = Query(None, description="Filter by section"),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Get approved questions for client questionnaire.

    Only returns questions with status='approved'.
    """
    settings = get_settings()

    from supabase import create_client

    supabase = create_client(settings.supabase_url, settings.supabase_service_key)

    query = (
        supabase.table("framework_questions")
        .select("*")
        .eq("project_id", project_id)
        .eq("status", "approved")
    )

    if section:
        query = query.eq("section_id", section)

    result = query.order("control_id").execute()

    return {
        "project_id": project_id,
        "total_approved": len(result.data),
        "questions": result.data,
    }
