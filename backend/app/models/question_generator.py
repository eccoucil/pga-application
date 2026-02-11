"""
Models for the enhanced QuestionGenerator with consultant persona and anti-hallucination.

This module provides:
- ConsultantPersona: Configurable professional persona for question generation
- QuestionConfidence: Multi-dimensional confidence scoring for questions
- ValidationResult: Post-generation validation results
"""

from typing import Optional

from pydantic import BaseModel, Field


class ConsultantPersona(BaseModel):
    """Configurable consultant persona for question generation."""

    name: str = Field(..., description="Consultant's name (e.g., 'Sarah Chen')")
    role: str = Field(
        default="Senior Compliance Consultant", description="Professional title"
    )
    goal: str = Field(
        default="Assess compliance maturity with precision and actionable insights",
        description="Primary objective",
    )
    backstory: str = Field(..., description="Professional background and experience")
    specialization: str = Field(
        ..., description="Areas of expertise (e.g., 'ISO 27001, BNM RMIT')"
    )
    years_experience: int = Field(default=15, ge=1, description="Years of experience")

    @classmethod
    def default(cls) -> "ConsultantPersona":
        """Create default persona."""
        return cls(
            name="Sarah Chen",
            backstory=(
                "15 years conducting 200+ compliance assessments across Banking, "
                "Insurance, Healthcare, and Technology sectors"
            ),
            specialization="ISO 27001:2022, BNM RMIT, financial services compliance",
        )

    @classmethod
    def for_industry(cls, industry: str) -> "ConsultantPersona":
        """
        Create industry-specific persona.

        Args:
            industry: Industry type string (e.g., "Banking & Financial Services")

        Returns:
            ConsultantPersona tailored to the industry
        """
        personas = {
            "Banking & Financial Services": cls(
                name="David Lim",
                role="Financial Services Compliance Lead",
                backstory=(
                    "20 years in banking compliance, former BNM examiner with "
                    "deep expertise in regulatory frameworks and risk management"
                ),
                specialization="BNM RMIT, Basel III, AML/CFT, PCI DSS",
                years_experience=20,
            ),
            "Insurance": cls(
                name="Rachel Tan",
                role="Insurance Compliance Specialist",
                backstory=(
                    "18 years in insurance compliance, specialized in underwriting "
                    "security and claims data protection"
                ),
                specialization="BNM guidelines, PDPA, actuarial data security",
                years_experience=18,
            ),
            "Healthcare": cls(
                name="Dr. Mei Wong",
                role="Healthcare Compliance Specialist",
                backstory=(
                    "Former hospital CISO with 12 years experience in healthcare "
                    "data protection and medical device security"
                ),
                specialization="Healthcare data protection, medical device security, PDPA",
                years_experience=12,
            ),
            "Technology": cls(
                name="Alex Kumar",
                role="Technology Security Consultant",
                backstory=(
                    "16 years in tech security, former CISO at multiple SaaS companies "
                    "with expertise in cloud security and DevSecOps"
                ),
                specialization="Cloud security, DevSecOps, API security, SOC 2",
                years_experience=16,
            ),
            "Manufacturing": cls(
                name="James Ong",
                role="Industrial Security Consultant",
                backstory=(
                    "14 years in manufacturing security, specialized in OT/ICS "
                    "security and supply chain risk management"
                ),
                specialization="OT/ICS security, supply chain security, ISO 27001",
                years_experience=14,
            ),
            "Government": cls(
                name="Aisha Rahman",
                role="Public Sector Security Advisor",
                backstory=(
                    "17 years in government cybersecurity, former agency CISO with "
                    "expertise in critical infrastructure protection"
                ),
                specialization="Critical infrastructure, ISMS, data sovereignty",
                years_experience=17,
            ),
            "Retail": cls(
                name="Michael Lee",
                role="Retail Security Consultant",
                backstory=(
                    "13 years in retail security, specialized in e-commerce security "
                    "and payment card protection"
                ),
                specialization="PCI DSS, e-commerce security, PDPA",
                years_experience=13,
            ),
        }
        return personas.get(industry, cls.default())


class QuestionConfidence(BaseModel):
    """
    Confidence breakdown for a generated question.

    Scoring logic:
    - grounding_score: 1.0 if exact quote found, 0.5 if partial match, 0.0 if not found
    - context_score: (referenced_items_that_exist / total_referenced_items)
    - specificity_score: 1.0 if uses org name + specific assets, 0.5 if generic

    Overall calculation:
        overall = (grounding_score * 0.35) + (context_score * 0.45) + (specificity_score * 0.20)

    Thresholds:
    - overall >= 0.90 = Question passes (95% confidence target)
    - grounding_score >= 0.85 = Factual accuracy met (85% target)
    """

    grounding_score: float = Field(
        ..., ge=0.0, le=1.0, description="Grounding quote verified in control text"
    )
    context_score: float = Field(
        ..., ge=0.0, le=1.0, description="Referenced data exists in context"
    )
    specificity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Uses specific vs generic terms"
    )
    overall: float = Field(..., ge=0.0, le=1.0, description="Weighted average")

    @classmethod
    def calculate(
        cls,
        grounding_score: float,
        context_score: float,
        specificity_score: float,
    ) -> "QuestionConfidence":
        """
        Calculate confidence scores with weighted average.

        Args:
            grounding_score: Score for grounding quote verification (0.0-1.0)
            context_score: Score for context reference verification (0.0-1.0)
            specificity_score: Score for specificity of language (0.0-1.0)

        Returns:
            QuestionConfidence with calculated overall score
        """
        overall = (
            (grounding_score * 0.35)
            + (context_score * 0.45)
            + (specificity_score * 0.20)
        )
        return cls(
            grounding_score=grounding_score,
            context_score=context_score,
            specificity_score=specificity_score,
            overall=overall,
        )

    def passes_threshold(self, overall_threshold: float = 0.90) -> bool:
        """Check if confidence meets the required threshold."""
        return self.overall >= overall_threshold

    def meets_factual_accuracy(self, grounding_threshold: float = 0.85) -> bool:
        """Check if grounding score meets factual accuracy threshold."""
        return self.grounding_score >= grounding_threshold


class ValidationResult(BaseModel):
    """
    Result of post-generation validation.

    Contains validation status and detailed breakdown of any issues found.
    """

    is_valid: bool = Field(
        ..., description="Whether the question passed all validation checks"
    )
    grounding_verified: bool = Field(
        ..., description="Whether grounding quote was found in control text"
    )
    context_references_verified: bool = Field(
        ..., description="Whether all referenced data exists in context"
    )
    hallucination_flags: list[str] = Field(
        default_factory=list,
        description="List of potential hallucinations detected",
    )
    confidence: QuestionConfidence = Field(
        ..., description="Detailed confidence breakdown"
    )
    validation_notes: Optional[str] = Field(
        None, description="Additional notes about validation"
    )

    def summary(self) -> str:
        """Return a brief summary of validation result."""
        if self.is_valid:
            return f"Valid (confidence: {self.confidence.overall:.2f})"
        flags = ", ".join(self.hallucination_flags[:3])
        return f"Invalid: {flags}"
