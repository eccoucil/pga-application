"""Questionnaire agent request and response models."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class GenerateWithCriteriaRequest(BaseModel):
    """Structured criteria for batch question generation (wizard flow)."""

    project_id: str = Field(..., description="Project UUID")
    assessment_id: Optional[str] = Field(
        None, description="Assessment UUID to link generated questions to"
    )

    # Step 1: Assessment Profile
    maturity_level: str = Field(
        ..., description="Organization's assessment maturity"
    )
    question_depth: str = Field(
        ..., description="Desired question depth/count per control"
    )

    # Step 2: Focus & Priorities
    priority_domains: list[str] = Field(
        default_factory=list,
        description="Control domains to emphasize (empty = all equal)",
    )
    compliance_concerns: Optional[str] = Field(
        None, description="Known gaps or specific concerns"
    )
    controls_to_skip: Optional[str] = Field(
        None, description="Controls to de-emphasize or skip"
    )
    questions_per_control: Optional[int] = Field(
        None, description="Override questions per control (default 3)"
    )


class GenerateQuestionRequest(BaseModel):
    """Request to start a new questionnaire generation session."""

    project_id: str = Field(..., description="Project UUID")
    assessment_id: Optional[str] = Field(
        None, description="Assessment UUID to link generated questions to"
    )


class RespondRequest(BaseModel):
    """Request to continue a session by answering the agent's question."""

    session_id: str = Field(
        ..., description="Session UUID from generate-question"
    )
    answer: str = Field(
        ..., min_length=1, description="User's answer to the agent's question"
    )


class AgentQuestion(BaseModel):
    """Returned when the agent wants to ask the user something."""

    session_id: str
    type: Literal["question"] = "question"
    question: str
    context: Optional[str] = None
    options: Optional[list[str]] = None


class GeneratedQuestion(BaseModel):
    """A single generated compliance question."""

    id: str
    question: str
    category: str
    priority: str
    expected_evidence: Optional[str] = None
    guidance_notes: Optional[str] = None


class ControlQuestions(BaseModel):
    """Questions generated for one framework control."""

    control_id: str
    control_title: str
    framework: str
    questions: list[GeneratedQuestion]


class QuestionnaireComplete(BaseModel):
    """Returned when the agent finishes generating all questions."""

    session_id: str
    type: Literal["complete"] = "complete"
    controls: list[ControlQuestions]
    total_controls: int
    total_questions: int
    generation_time_ms: int
    criteria_summary: str


class GenerationRedirect(BaseModel):
    """Returned when the conversational agent triggers batch generation."""

    session_id: str
    type: Literal["generation_redirect"] = "generation_redirect"
    criteria: dict


# Union response type
QuestionnaireResponse = AgentQuestion | QuestionnaireComplete | GenerationRedirect
