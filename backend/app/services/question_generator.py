"""
Question Generator Service using OpenAI GPT-4o.

Generates 5 perspective-based questions per control using the unified
context profile for industry-specific, contextual compliance questions.

Enhanced with:
- Consultant persona (role, goal, backstory) for professional framing
- Anti-hallucination rules to prevent fabricated references
- Post-generation validation for 95% confidence / 85% factual accuracy

Question Perspectives:
1. Policy Existence - Does a policy exist?
2. Implementation - How is it implemented?
3. Evidence - What proof exists?
4. Operational Effectiveness - Is it working?
5. Continuous Improvement - How is it maintained?
"""

import json
import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

import openai
from pydantic import BaseModel, Field

from app.config import get_settings
from app.models.question_generator import (
    ConsultantPersona,
    QuestionConfidence,
    ValidationResult,
)
from app.services.context_aggregator import (
    UnifiedContextProfile,
    get_context_aggregator,
)
from app.services.question_validator import get_question_validator

logger = logging.getLogger(__name__)

# OpenAI model for question generation
OPENAI_MODEL = "gpt-4o"

# Validation thresholds
OVERALL_CONFIDENCE_THRESHOLD = 0.90
GROUNDING_ACCURACY_THRESHOLD = 0.85


class GeneratedQuestion(BaseModel):
    """A single generated question with metadata."""

    question_number: int = Field(..., ge=1, le=5)
    question_text: str
    question_type: str = Field(
        ...,
        description="Question perspective: policy_existence, implementation, "
        "evidence, operational_effectiveness, continuous_improvement",
    )
    expected_evidence: list[str] = Field(default_factory=list)
    grounding_source: str = Field(
        ..., description="Quote from control text justifying the question"
    )
    context_source: str = Field(
        ..., description="Which context data informed the customization"
    )
    # New fields for validation
    confidence: Optional[QuestionConfidence] = Field(
        None, description="Confidence scores from validation"
    )
    validation_status: str = Field(
        default="pending",
        description="Validation status: pending, validated, flagged",
    )


class ControlQuestionSet(BaseModel):
    """Set of 5 questions for a single control."""

    control_id: str
    control_title: str
    control_description: Optional[str] = None
    questions: list[GeneratedQuestion]
    priority: str = "medium"  # critical, high, medium, low
    batch_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    # New fields
    persona_used: Optional[str] = Field(
        None, description="Name of consultant persona used"
    )
    validation_summary: Optional[dict] = Field(
        None, description="Summary of validation results"
    )


class ControlDefinition(BaseModel):
    """Control definition from iso_requirements or bnm_rmit_requirements."""

    identifier: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    key_activities: list[str] = Field(default_factory=list)


# Consultant Persona Prompt Template
CONSULTANT_PERSONA_TEMPLATE = """## Your Identity

You are **{persona_name}**, a {persona_role} with {persona_years} years of experience.

**Your Background:**
{persona_backstory}

**Your Specialization:**
{persona_specialization}

**Your Goal:**
Assess {organization_name}'s compliance maturity with precision. Your questions must:
1. Be grounded in specific control requirements (cite exact quotes)
2. Reference ONLY data that exists in the provided context
3. Be answerable with concrete, obtainable evidence

**Your Professional Approach:**
- You NEVER assume - you verify with evidence
- You reference specific systems and documents you KNOW exist
- You acknowledge when information is limited rather than fabricating details
- You speak directly to the client using their organization name
"""

# Anti-Hallucination Rules
ANTI_HALLUCINATION_RULES = """## CRITICAL: Factual Accuracy Rules (85% Minimum)

You MUST follow these rules to achieve 85% factual accuracy:

### Rule 1: Only Reference Existing Data
- Digital assets: ONLY mention URLs from `discovered_context.digital_assets`
- Technologies: ONLY mention items from `technology_hints`
- Certifications: ONLY mention items from `certifications`
- If a category is empty, do NOT reference it

### Rule 2: Never Fabricate
- Do NOT invent system names, portal names, or URLs
- Do NOT assume technologies exist unless explicitly listed
- Do NOT create fictional policy document names
- Do NOT guess at organizational structure

### Rule 3: Mark Uncertainty
- If context data is sparse: "Based on the available information..."
- If no digital assets: Ask general questions, not system-specific ones
- If controls_addressed is empty: Focus on policy existence, not gaps

### Rule 4: Exact Grounding Required
- `grounding_source`: MUST be a VERBATIM quote from control_description or key_activities
- `context_source`: MUST list EXACT field paths used (e.g., "discovered_context.digital_assets[0].url")

### Rule 5: Self-Validation Checklist
Before outputting each question, verify:
- [ ] Every asset/URL mentioned exists in the context inventory
- [ ] Grounding quote is copied exactly from control text
- [ ] Organization name "{organization_name}" is used (not "the organization")
- [ ] No invented systems, technologies, or document names
"""

# Main Question Generation Prompt
QUESTION_GENERATION_PROMPT = """{consultant_persona}

{anti_hallucination_rules}

{context_inventory}

## Control to Assess

**Control ID**: {control_id}
**Control Title**: {control_title}
**Control Description**: {control_description}
**Key Activities**: {key_activities}

## Question Generation Requirements

Generate exactly 5 questions, one for each perspective:

1. **Policy Existence** (question_type: "policy_existence")
   - Focus: Does {organization_name}'s {department} department have a documented policy/procedure for this control?
   - Ask about specific policy documents covering {department} responsibilities
   - Reference department-specific assets: {department_assets}

2. **Implementation** (question_type: "implementation")
   - Focus: How does {organization_name}'s {department} department implement this control in practice?
   - Reference department-specific assets and systems
   - Ask about key controls relevant to {department}: {department_controls}

3. **Evidence** (question_type: "evidence")
   - Focus: What proof/artifacts can {organization_name}'s {department} department provide demonstrating compliance?
   - Request specific evidence types for {department}: {department_evidence}
   - Reference specific assets or systems ONLY if they exist in the inventory

4. **Operational Effectiveness** (question_type: "operational_effectiveness")
   - Focus: Is the control working as intended within {organization_name}'s {department} department?
   - Ask about testing, audits, reviews specific to {department} operations
   - Consider department-specific risks: {department_risks}

5. **Continuous Improvement** (question_type: "continuous_improvement")
   - Focus: How does {organization_name}'s {department} department monitor and improve this control?
   - Ask about update processes, lessons learned within {department}
   - Consider both industry risks ({industry_risks}) and department risks

## Department-Specific Focus

This assessment targets the **{department}** department. ALL questions MUST be tailored to this department.

### Department Risks to Consider
{department_risks}

### Primary Assets to Inquire About
{department_assets}

### Key Controls for This Department
{department_controls}

### Evidence Types to Request
{department_evidence}

**CRITICAL**: Do NOT ask generic organization-wide questions. Every question MUST reference {department} department responsibilities, assets, or processes.

Example of correct framing:
- WRONG: "Does your organization have an access control policy?"
- RIGHT: "Does {organization_name}'s {department} department have documented procedures for managing access to {department_asset_example}?"

## Industry-Specific Adjustments

Based on {organization_name}'s industry ({industry_type}), adjust questions to:
- Reference industry-specific regulations and standards
- Focus on industry-relevant risks
- Consider regulatory pressure level: {regulatory_pressure}

## Output Format

Return a JSON object with exactly this structure:
```json
{{
  "questions": [
    {{
      "question_number": 1,
      "question_text": "Does {organization_name} have a documented...",
      "question_type": "policy_existence",
      "expected_evidence": ["Policy document", "Procedure manual"],
      "grounding_source": "EXACT: 'verbatim quote from control text'",
      "context_source": "organization.name, organization.industry_type",
      "self_validation": {{
        "grounding_is_exact_quote": true,
        "all_references_in_inventory": true,
        "no_fabricated_data": true
      }}
    }}
  ],
  "priority": "high",
  "confidence_summary": {{
    "all_questions_grounded": true,
    "context_coverage_percent": 80
  }}
}}
```

## Priority Determination

Set priority based on:
- **critical**: Control relates to discovered digital assets with high exposure
- **high**: No existing policies reference this control (gap identified)
- **medium**: Default for controls with some coverage
- **low**: Control fully addressed by existing policies

## Existing Policies Context

Controls already addressed by documents: {controls_addressed}

If this control is in the list above, focus questions on evidence and effectiveness.
If not in the list, focus on policy existence and implementation.

Generate the 5 questions now:"""


class QuestionGenerator:
    """
    Generates contextual compliance questions using Claude Opus 4.5.

    Enhanced with consultant persona and anti-hallucination validation.

    Usage:
        generator = QuestionGenerator()
        questions = await generator.generate_for_control(
            control=ControlDefinition(...),
            context=UnifiedContextProfile(...),
        )
    """

    def __init__(self, persona: Optional[ConsultantPersona] = None):
        """
        Initialize the question generator.

        Args:
            persona: Optional default persona. If not provided, persona will be
                     selected based on industry context for each request.
        """
        settings = get_settings()
        self._client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = OPENAI_MODEL
        self._context_aggregator = get_context_aggregator()
        self._default_persona = persona
        self._validator = get_question_validator()

    async def generate_for_control(
        self,
        control: ControlDefinition,
        context: UnifiedContextProfile,
        batch_id: Optional[str] = None,
        persona: Optional[ConsultantPersona] = None,
        skip_validation: bool = False,
    ) -> ControlQuestionSet:
        """
        Generate 5 questions for a single control.

        Args:
            control: The control definition to generate questions for
            context: Unified context profile with organization data
            batch_id: Optional batch ID for grouping questions
            persona: Optional persona override for this request
            skip_validation: Skip post-generation validation (for testing)

        Returns:
            ControlQuestionSet with 5 generated questions
        """
        if batch_id is None:
            batch_id = str(uuid4())

        # Select persona: provided > default > industry-specific
        active_persona = (
            persona
            or self._default_persona
            or ConsultantPersona.for_industry(context.organization.industry_type or "")
        )

        # Build the prompt with persona and anti-hallucination rules
        prompt = self._build_prompt(control, context, active_persona)

        try:
            # Call OpenAI GPT-4o
            response = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse the response
            content = response.choices[0].message.content
            questions = self._parse_response(
                content, control, batch_id, active_persona.name
            )

            # Post-generation validation
            if not skip_validation:
                questions = self._validate_questions(questions, control, context)

            logger.info(
                f"Generated {len(questions.questions)} questions for "
                f"control {control.identifier} (persona: {active_persona.name})"
            )

            return questions

        except Exception as e:
            logger.error(f"Failed to generate questions for {control.identifier}: {e}")
            raise

    async def generate_for_section(
        self,
        controls: list[ControlDefinition],
        client_id: str,
        project_id: str,
        section: str,
        framework: str = "iso_27001",
        persona: Optional[ConsultantPersona] = None,
    ) -> list[ControlQuestionSet]:
        """
        Generate questions for all controls in a section.

        Args:
            controls: List of control definitions in the section
            client_id: Client UUID
            project_id: Project UUID
            section: Section ID (e.g., "A.5")
            framework: Framework type
            persona: Optional persona override for all questions

        Returns:
            List of ControlQuestionSet for each control
        """
        # Build context for this section
        context = await self._context_aggregator.build_context(
            client_id=client_id,
            project_id=project_id,
            section=section,
            framework=framework,
        )

        batch_id = str(uuid4())
        results = []

        for control in controls:
            try:
                question_set = await self.generate_for_control(
                    control=control,
                    context=context,
                    batch_id=batch_id,
                    persona=persona,
                )
                results.append(question_set)
            except Exception as e:
                logger.error(f"Failed to generate for {control.identifier}: {e}")
                # Continue with other controls

        return results

    def _build_prompt(
        self,
        control: ControlDefinition,
        context: UnifiedContextProfile,
        persona: ConsultantPersona,
    ) -> str:
        """Build the prompt with persona, anti-hallucination rules, and context."""
        # Build consultant persona section
        consultant_persona = CONSULTANT_PERSONA_TEMPLATE.format(
            persona_name=persona.name,
            persona_role=persona.role,
            persona_years=persona.years_experience,
            persona_backstory=persona.backstory,
            persona_specialization=persona.specialization,
            organization_name=context.organization.name,
        )

        # Build anti-hallucination rules
        anti_hallucination = ANTI_HALLUCINATION_RULES.format(
            organization_name=context.organization.name,
        )

        # Build context inventory
        context_inventory = self._build_context_inventory(context)

        # Extract department-specific data
        department = context.organization.department or "General"
        dept_focus = context.risk_profile.department_focus or {}

        # Format department risks (from risk profile)
        department_risks_list = context.risk_profile.department_risks[:5]
        department_risks = (
            "\n".join(f"- {r}" for r in department_risks_list)
            if department_risks_list
            else "- General departmental security risks"
        )

        # Format department assets
        dept_assets = dept_focus.get("primary_assets", [])
        department_assets = (
            "\n".join(f"- {a}" for a in dept_assets)
            if dept_assets
            else "- Department-specific data and systems"
        )

        # Format department controls
        dept_controls = dept_focus.get("key_controls", [])
        department_controls = (
            "\n".join(f"- {c}" for c in dept_controls)
            if dept_controls
            else "- Standard departmental controls"
        )

        # Format department evidence types
        dept_evidence = dept_focus.get("evidence_types", [])
        department_evidence = (
            "\n".join(f"- {e}" for e in dept_evidence)
            if dept_evidence
            else "- Policies, procedures, and records"
        )

        # Get example asset for question framing
        department_asset_example = (
            dept_assets[0] if dept_assets else "department data and systems"
        )

        return QUESTION_GENERATION_PROMPT.format(
            consultant_persona=consultant_persona,
            anti_hallucination_rules=anti_hallucination,
            context_inventory=context_inventory,
            control_id=control.identifier,
            control_title=control.title,
            control_description=control.description or "Not provided",
            key_activities=(
                ", ".join(control.key_activities)
                if control.key_activities
                else "Not specified"
            ),
            organization_name=context.organization.name,
            industry_type=context.organization.industry_type or "General",
            industry_risks=", ".join(context.risk_profile.industry_risks[:3]),
            regulatory_pressure=context.risk_profile.regulatory_pressure,
            controls_addressed=(
                ", ".join(context.existing_policies.controls_addressed[:10])
                or "None identified"
            ),
            # Department-specific variables
            department=department,
            department_risks=department_risks,
            department_assets=department_assets,
            department_controls=department_controls,
            department_evidence=department_evidence,
            department_asset_example=department_asset_example,
        )

    def _build_context_inventory(self, context: UnifiedContextProfile) -> str:
        """Build explicit inventory of available data for Claude."""
        # Format digital assets
        assets = context.discovered_context.digital_assets
        if assets:
            assets_list = "\n".join(
                [
                    f"  - {a.url} ({a.asset_type}): {a.purpose or 'No description'}"
                    for a in assets
                ]
            )
        else:
            assets_list = "  None available - do NOT reference specific URLs or portals"

        # Format technologies
        techs = context.discovered_context.technology_hints
        tech_list = (
            ", ".join(techs)
            if techs
            else "None available - do NOT reference specific technologies"
        )

        # Format certifications
        certs = context.discovered_context.certifications
        cert_list = (
            ", ".join(certs)
            if certs
            else "None available - do NOT reference specific certifications"
        )

        # Format controls addressed
        controls = context.existing_policies.controls_addressed
        controls_list = (
            ", ".join(controls[:10])
            if controls
            else "None identified - focus on policy existence"
        )

        # Format services
        services = context.discovered_context.services
        services_list = ", ".join(services) if services else "None specified"

        return f"""## Context Data Inventory (Reference ONLY these items)

### Organization
- Name: {context.organization.name}
- Industry: {context.organization.industry_type or "Not specified"}
- Department: {context.organization.department or "Not specified"}
- Nature of Business: {context.organization.nature_of_business or "Not specified"}
- ISMS Scope: {context.organization.scope_statement_isms or "Not specified"}
- Web Domain: {context.organization.web_domain or "Not specified"}

### Digital Assets ({len(assets)} available)
{assets_list}

### Technologies ({len(techs)} available)
{tech_list}

### Certifications ({len(certs)} available)
{cert_list}

### Services ({len(services)} available)
{services_list}

### Controls Already Addressed ({len(controls)} identified)
{controls_list}

**IMPORTANT:** If a section shows "None available", do NOT ask questions about that category.
Instead, ask general questions appropriate for an organization without that data."""

    def _parse_response(
        self,
        content: str,
        control: ControlDefinition,
        batch_id: str,
        persona_name: str,
    ) -> ControlQuestionSet:
        """Parse Claude's response into structured questions."""
        try:
            # Extract JSON from response
            json_str = self._extract_json(content)
            data = json.loads(json_str)

            questions = []
            for q in data.get("questions", []):
                questions.append(
                    GeneratedQuestion(
                        question_number=q["question_number"],
                        question_text=q["question_text"],
                        question_type=q["question_type"],
                        expected_evidence=q.get("expected_evidence", []),
                        grounding_source=q.get("grounding_source", ""),
                        context_source=q.get("context_source", ""),
                        validation_status="pending",
                    )
                )

            priority = data.get("priority", "medium")
            confidence_summary = data.get("confidence_summary")

            return ControlQuestionSet(
                control_id=control.identifier,
                control_title=control.title,
                control_description=control.description,
                questions=questions,
                priority=priority,
                batch_id=batch_id,
                persona_used=persona_name,
                validation_summary=confidence_summary,
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw content: {content}")
            # Return empty set on parse failure
            return ControlQuestionSet(
                control_id=control.identifier,
                control_title=control.title,
                control_description=control.description,
                questions=[],
                priority="medium",
                batch_id=batch_id,
                persona_used=persona_name,
            )

    def _extract_json(self, content: str) -> str:
        """Extract JSON from markdown or raw response."""
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.find("```", json_start)
            return content[json_start:json_end].strip()
        elif "```" in content:
            json_start = content.find("```") + 3
            json_end = content.find("```", json_start)
            return content[json_start:json_end].strip()
        else:
            # Try to find JSON object directly
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            return content[json_start:json_end]

    def _validate_questions(
        self,
        question_set: ControlQuestionSet,
        control: ControlDefinition,
        context: UnifiedContextProfile,
    ) -> ControlQuestionSet:
        """
        Validate all questions and filter out those that fail thresholds.

        Args:
            question_set: The generated questions
            control: The control definition
            context: The unified context profile

        Returns:
            Updated ControlQuestionSet with validated questions
        """
        validated_questions = []
        validation_results = []

        for question in question_set.questions:
            result: ValidationResult = self._validator.validate_question(
                question, control, context
            )

            if result.confidence.overall >= OVERALL_CONFIDENCE_THRESHOLD:
                # Question passed validation
                question.confidence = result.confidence
                question.validation_status = "validated"
                validated_questions.append(question)
                validation_results.append(
                    {
                        "question_number": question.question_number,
                        "status": "validated",
                        "confidence": result.confidence.overall,
                    }
                )
            else:
                # Question failed validation
                logger.warning(
                    f"Question {question.question_number} for {control.identifier} "
                    f"failed validation: confidence={result.confidence.overall:.2f}, "
                    f"flags={result.hallucination_flags}"
                )
                validation_results.append(
                    {
                        "question_number": question.question_number,
                        "status": "flagged",
                        "confidence": result.confidence.overall,
                        "flags": result.hallucination_flags,
                    }
                )

        # Update question set
        question_set.questions = validated_questions
        question_set.validation_summary = {
            "total_generated": len(validation_results),
            "total_validated": len(validated_questions),
            "results": validation_results,
        }

        if len(validated_questions) < len(validation_results):
            logger.info(
                f"Filtered {len(validation_results) - len(validated_questions)} "
                f"questions for {control.identifier} due to validation failures"
            )

        return question_set


# Singleton pattern
_question_generator: Optional[QuestionGenerator] = None


def get_question_generator(
    persona: Optional[ConsultantPersona] = None,
) -> QuestionGenerator:
    """
    Get cached QuestionGenerator instance.

    Args:
        persona: Optional default persona. Only used when creating new instance.
    """
    global _question_generator
    if _question_generator is None:
        _question_generator = QuestionGenerator(persona=persona)
    return _question_generator


def reset_question_generator() -> None:
    """Reset generator for testing."""
    global _question_generator
    _question_generator = None
