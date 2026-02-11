"""
Question Validator Service for anti-hallucination and grounding verification.

Validates generated questions to ensure:
1. Grounding quotes exist in control text
2. Referenced assets/technologies exist in context
3. No fabricated data is included

Targets:
- 95% confidence (overall >= 0.90)
- 85% factual accuracy (grounding_score >= 0.85)
"""

import logging
import re
from typing import TYPE_CHECKING

from app.models.question_generator import QuestionConfidence, ValidationResult

if TYPE_CHECKING:
    from app.services.context_aggregator import UnifiedContextProfile
    from app.services.question_generator import ControlDefinition, GeneratedQuestion

logger = logging.getLogger(__name__)

# Patterns for extracting references from question text
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+|(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/[^\s]*)?")
SYSTEM_NAME_PATTERN = re.compile(
    r"\b(?:portal|system|platform|api|dashboard|application|server|database|service)\s+"
    r"(?:named?\s+)?['\"]?([A-Z][a-zA-Z0-9_-]+)['\"]?",
    re.IGNORECASE,
)
TECHNOLOGY_PATTERN = re.compile(
    r"\b(AWS|Azure|GCP|Kubernetes|Docker|PostgreSQL|MySQL|MongoDB|Redis|"
    r"Elasticsearch|Kafka|RabbitMQ|Jenkins|GitLab|GitHub|Terraform|Ansible|"
    r"React|Angular|Vue|Node\.js|Python|Java|\.NET|Spring|Django|FastAPI|"
    r"OAuth|SAML|LDAP|Active Directory|Okta|Auth0|Cloudflare|WAF|SIEM|"
    r"Splunk|ELK|Prometheus|Grafana|Datadog|PagerDuty)\b",
    re.IGNORECASE,
)


class QuestionValidator:
    """
    Validates questions for hallucinations and grounding.

    Performs three key checks:
    1. Grounding verification - Does the cited quote exist in control text?
    2. Reference verification - Do mentioned assets/technologies exist in context?
    3. Specificity check - Does the question use specific vs generic language?
    """

    def validate_question(
        self,
        question: "GeneratedQuestion",
        control: "ControlDefinition",
        context: "UnifiedContextProfile",
    ) -> ValidationResult:
        """
        Validate a question meets 95% confidence / 85% factual thresholds.

        Args:
            question: The generated question to validate
            control: The control definition the question is based on
            context: The unified context profile with organization data

        Returns:
            ValidationResult with detailed validation breakdown
        """
        # Check 1: Verify grounding quote exists in control text
        grounding_verified, grounding_score = self._verify_grounding(
            question.grounding_source, control
        )

        # Check 2: Extract and verify references in question text
        references = self._extract_references(question.question_text)
        context_verified, hallucination_flags = self._verify_references_exist(
            references, context
        )

        # Calculate context score
        total_refs = (
            len(references["urls"])
            + len(references["systems"])
            + len(references["technologies"])
        )
        if total_refs > 0:
            verified_count = total_refs - len(hallucination_flags)
            context_score = max(0.0, verified_count / total_refs)
        else:
            # No external references = perfect context score
            context_score = 1.0

        # Check 3: Specificity score
        specificity_score = self._calculate_specificity(question.question_text, context)

        # Calculate overall confidence
        confidence = QuestionConfidence.calculate(
            grounding_score=grounding_score,
            context_score=context_score,
            specificity_score=specificity_score,
        )

        # Determine overall validity
        is_valid = confidence.passes_threshold(
            0.90
        ) and confidence.meets_factual_accuracy(0.85)

        # Add grounding issues to hallucination flags if needed
        if not grounding_verified:
            hallucination_flags.insert(0, "Grounding quote not found in control text")

        return ValidationResult(
            is_valid=is_valid,
            grounding_verified=grounding_verified,
            context_references_verified=context_verified,
            hallucination_flags=hallucination_flags,
            confidence=confidence,
            validation_notes=self._generate_notes(
                grounding_verified, context_verified, hallucination_flags
            ),
        )

    def _verify_grounding(
        self, grounding_source: str, control: "ControlDefinition"
    ) -> tuple[bool, float]:
        """
        Check if grounding quote exists in control description or key_activities.

        Args:
            grounding_source: The quoted text from the question
            control: The control definition to search

        Returns:
            Tuple of (verified: bool, score: float)
        """
        if not grounding_source:
            return False, 0.0

        # Clean up the grounding source
        clean_source = self._clean_quote(grounding_source)
        if not clean_source or len(clean_source) < 5:
            return False, 0.0

        # Build searchable text from control
        search_text = self._build_control_text(control).lower()
        clean_source_lower = clean_source.lower()

        # Exact substring match
        if clean_source_lower in search_text:
            return True, 1.0

        # Partial match - check if significant words are present
        words = [w for w in clean_source_lower.split() if len(w) > 3]
        if words:
            matches = sum(1 for w in words if w in search_text)
            ratio = matches / len(words)
            if ratio >= 0.8:
                return True, 0.8
            if ratio >= 0.5:
                return False, 0.5

        return False, 0.0

    def _clean_quote(self, grounding_source: str) -> str:
        """Clean up a grounding quote by removing prefixes and quotes."""
        # Remove common prefixes
        prefixes = [
            "Quote from control:",
            "EXACT:",
            "From control:",
            "Control text:",
            "Based on:",
        ]
        result = grounding_source.strip()
        for prefix in prefixes:
            if result.lower().startswith(prefix.lower()):
                result = result[len(prefix) :].strip()

        # Remove surrounding quotes
        if result.startswith(("'", '"')) and result.endswith(("'", '"')):
            result = result[1:-1]

        return result.strip()

    def _build_control_text(self, control: "ControlDefinition") -> str:
        """Build searchable text from control definition."""
        parts = [control.title]
        if control.description:
            parts.append(control.description)
        if control.key_activities:
            parts.extend(control.key_activities)
        if control.category:
            parts.append(control.category)
        return " ".join(parts)

    def _extract_references(self, question_text: str) -> dict:
        """
        Extract URLs, system names, and technologies mentioned in question.

        Args:
            question_text: The question text to analyze

        Returns:
            Dict with keys: urls, systems, technologies
        """
        urls = URL_PATTERN.findall(question_text)
        systems = SYSTEM_NAME_PATTERN.findall(question_text)
        technologies = TECHNOLOGY_PATTERN.findall(question_text)

        # Deduplicate and normalize
        return {
            "urls": list(set(url.lower().rstrip("/") for url in urls)),
            "systems": list(set(s.lower() for s in systems if s)),
            "technologies": list(set(t.lower() for t in technologies)),
        }

    def _verify_references_exist(
        self, references: dict, context: "UnifiedContextProfile"
    ) -> tuple[bool, list[str]]:
        """
        Verify extracted references exist in context.

        Args:
            references: Dict of extracted references
            context: The unified context profile

        Returns:
            Tuple of (all_verified: bool, hallucinated_items: list[str])
        """
        hallucinated = []

        # Build lookup sets from context
        context_urls = set()
        for asset in context.discovered_context.digital_assets:
            url_normalized = asset.url.lower().rstrip("/")
            context_urls.add(url_normalized)
            # Also add domain portion
            if "://" in asset.url:
                domain = asset.url.split("://")[1].split("/")[0].lower()
                context_urls.add(domain)

        context_techs = set(
            t.lower() for t in context.discovered_context.technology_hints
        )

        # Check URLs
        for url in references["urls"]:
            # Skip generic domains that are likely just examples
            if url in ("example.com", "localhost", "127.0.0.1"):
                continue
            # Check if URL or its domain exists in context
            url_found = False
            for ctx_url in context_urls:
                if url in ctx_url or ctx_url in url:
                    url_found = True
                    break
            if not url_found and context_urls:
                # Only flag if we have context URLs (otherwise generic questions are ok)
                hallucinated.append(f"URL '{url}' not in discovered digital_assets")

        # Check technologies - only flag if we have technology context
        if context_techs:
            for tech in references["technologies"]:
                if tech not in context_techs:
                    # Check for partial matches
                    found = any(tech in ct or ct in tech for ct in context_techs)
                    if not found:
                        hallucinated.append(
                            f"Technology '{tech}' not in technology_hints"
                        )

        # System names are harder to verify - only flag obvious fabrications
        # For now, we don't strictly validate system names as they may be
        # legitimately derived from context descriptions

        all_verified = len(hallucinated) == 0
        return all_verified, hallucinated

    def _calculate_specificity(
        self, question_text: str, context: "UnifiedContextProfile"
    ) -> float:
        """
        Calculate specificity score based on use of specific vs generic terms.

        Args:
            question_text: The question text to analyze
            context: The unified context profile

        Returns:
            Specificity score from 0.0 to 1.0
        """
        score = 0.5  # Base score for average specificity

        org_name = context.organization.name.lower()
        question_lower = question_text.lower()

        # Bonus for using organization name
        if org_name in question_lower:
            score += 0.25

        # Bonus for referencing specific assets
        for asset in context.discovered_context.digital_assets:
            if asset.url.lower() in question_lower:
                score += 0.15
                break

        # Penalty for generic phrases
        generic_phrases = [
            "the organization",
            "your organization",
            "your company",
            "the company",
            "relevant systems",
            "applicable assets",
        ]
        for phrase in generic_phrases:
            if phrase in question_lower:
                score -= 0.1

        return max(0.0, min(1.0, score))

    def _generate_notes(
        self,
        grounding_verified: bool,
        context_verified: bool,
        hallucination_flags: list[str],
    ) -> str | None:
        """Generate validation notes summarizing issues."""
        notes = []

        if not grounding_verified:
            notes.append("Grounding quote could not be verified in control text")

        if not context_verified:
            notes.append(f"Found {len(hallucination_flags)} potential hallucinations")

        if not notes:
            return None

        return "; ".join(notes)


# Singleton pattern
_question_validator: QuestionValidator | None = None


def get_question_validator() -> QuestionValidator:
    """Get cached QuestionValidator instance."""
    global _question_validator
    if _question_validator is None:
        _question_validator = QuestionValidator()
    return _question_validator


def reset_question_validator() -> None:
    """Reset validator for testing."""
    global _question_validator
    _question_validator = None
