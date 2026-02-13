"""Questionnaire generation router — conversational agent endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import get_current_user
from app.models.questionnaire import (
    GenerateQuestionRequest,
    GenerateWithCriteriaRequest,
    QuestionnaireComplete,
    QuestionnaireResponse,
    RespondRequest,
)
from app.services.questionnaire_agent import get_questionnaire_agent

router = APIRouter(prefix="/questionnaire", tags=["questionnaire"])


@router.post("/generate-with-criteria")
async def generate_with_criteria(
    request: GenerateWithCriteriaRequest,
    current_user: dict = Depends(get_current_user),
) -> QuestionnaireComplete:
    """Generate compliance questions from structured wizard criteria.

    Skips the conversational loop — all criteria are provided upfront.
    """
    agent = await get_questionnaire_agent()
    return await agent.generate_with_criteria(
        project_id=request.project_id,
        user_id=current_user["user_id"],
        maturity_level=request.maturity_level,
        question_depth=request.question_depth,
        priority_domains=request.priority_domains,
        compliance_concerns=request.compliance_concerns,
        controls_to_skip=request.controls_to_skip,
        assessment_id=request.assessment_id,
    )


@router.post("/generate-question")
async def generate_question(
    request: GenerateQuestionRequest,
    current_user: dict = Depends(get_current_user),
) -> QuestionnaireResponse:
    """Start a new questionnaire generation session.

    Fetches project context, then the agent asks clarifying questions
    before generating compliance questions for all framework controls.
    """
    agent = await get_questionnaire_agent()
    return await agent.start_session(
        request.project_id, current_user["user_id"], request.assessment_id
    )


@router.post("/respond")
async def respond_to_agent(
    request: RespondRequest,
    current_user: dict = Depends(get_current_user),
) -> QuestionnaireResponse:
    """Continue a questionnaire session by answering the agent's question.

    Returns either another question or the final generated questions.
    """
    agent = await get_questionnaire_agent()
    try:
        return await agent.continue_session(request.session_id, request.answer)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ------------------------------------------------------------------
# Retrieval endpoints
# ------------------------------------------------------------------


@router.get("/sessions")
async def list_sessions(
    project_id: str = Query(..., description="Project UUID"),
    assessment_id: str | None = Query(None, description="Filter by assessment UUID"),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    """List questionnaire sessions for a project, optionally filtered by assessment."""
    from app.db.supabase import get_async_supabase_client_async

    sb = await get_async_supabase_client_async()
    query = (
        sb.table("questionnaire_sessions")
        .select(
            "id, status, total_questions, total_controls, created_at, assessment_id"
        )
        .eq("project_id", project_id)
        .order("created_at", desc=True)
    )
    if assessment_id:
        query = query.eq("assessment_id", assessment_id)

    result = await query.execute()
    return result.data or []


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Retrieve a full questionnaire session including generated questions."""
    from app.db.supabase import get_async_supabase_client_async

    sb = await get_async_supabase_client_async()
    result = (
        await sb.table("questionnaire_sessions")
        .select("*")
        .eq("id", session_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Session not found")
    return result.data
