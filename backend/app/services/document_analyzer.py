"""
Claude-powered document policy analyzer.

Analyzes extracted document text to determine if it's a policy document,
extract metadata, and map to ISO 27001 / BNM RMIT controls.

Uses existing ANTHROPIC_API_KEY and claude_model from config.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import anthropic

from app.config import get_settings

logger = logging.getLogger(__name__)


class PolicyType(str, Enum):
    """Types of policy documents."""

    INFORMATION_SECURITY = "information_security"
    ACCESS_CONTROL = "access_control"
    DATA_PROTECTION = "data_protection"
    BUSINESS_CONTINUITY = "business_continuity"
    INCIDENT_RESPONSE = "incident_response"
    RISK_MANAGEMENT = "risk_management"
    ACCEPTABLE_USE = "acceptable_use"
    CHANGE_MANAGEMENT = "change_management"
    PHYSICAL_SECURITY = "physical_security"
    HUMAN_RESOURCES = "human_resources"
    COMPLIANCE = "compliance"
    NETWORK_SECURITY = "network_security"
    CRYPTOGRAPHY = "cryptography"
    SUPPLIER_MANAGEMENT = "supplier_management"
    OTHER = "other"


@dataclass
class ControlMapping:
    """A mapping from a policy to a compliance control."""

    framework: str  # "iso27001" or "bnm_rmit"
    identifier: str  # e.g. "A.5.1" or "8.1"
    title: str
    compliance_level: str  # compliant / partially_compliant / non_compliant
    evidence: str  # Quote from the document
    gap: Optional[str] = None  # Description of gap if not fully compliant


@dataclass
class PolicyAnalysisResult:
    """Result of analyzing a document for policy content."""

    is_policy: bool
    policy_type: Optional[str] = None
    title: Optional[str] = None
    version: Optional[str] = None
    effective_date: Optional[str] = None
    scope_summary: Optional[str] = None
    controls_addressed: list[ControlMapping] = field(default_factory=list)
    confidence: float = 0.0


ANALYSIS_SYSTEM_PROMPT = """You are a compliance document analyst specializing in ISO 27001:2022 and BNM RMIT frameworks.

Analyze the provided document text and determine:

1. **Is this a policy document?** (security policy, procedure, standard, guideline)
2. **Policy metadata**: title, version, effective date, scope
3. **Control mappings**: Which ISO 27001:2022 Annex A controls or BNM RMIT requirements does this policy address?

For each control mapping, provide:
- The framework ("iso27001" or "bnm_rmit")
- The control identifier (e.g., "A.5.1" for ISO, "8.1" for BNM RMIT)
- The control title
- Compliance level: "compliant" (fully addresses), "partially_compliant" (addresses some aspects), or "non_compliant" (contradicts or misses key aspects)
- Evidence: Quote the exact text from the document that supports this mapping
- Gap: If not fully compliant, describe what's missing

You MUST return valid JSON with this exact structure:
{
    "is_policy": true/false,
    "policy_type": "one of: information_security, access_control, data_protection, business_continuity, incident_response, risk_management, acceptable_use, change_management, physical_security, human_resources, compliance, network_security, cryptography, supplier_management, other",
    "title": "string or null",
    "version": "string or null",
    "effective_date": "string or null",
    "scope_summary": "Brief summary of what the policy covers",
    "controls_addressed": [
        {
            "framework": "iso27001",
            "identifier": "A.5.1",
            "title": "Policies for information security",
            "compliance_level": "compliant",
            "evidence": "Exact quote from document...",
            "gap": null
        }
    ],
    "confidence": 0.0 to 1.0
}

If the document is NOT a policy (e.g., a spreadsheet, financial report, marketing material):
{
    "is_policy": false,
    "policy_type": null,
    "title": null,
    "version": null,
    "effective_date": null,
    "scope_summary": null,
    "controls_addressed": [],
    "confidence": 0.9
}

IMPORTANT:
- Only map controls you can support with direct evidence from the text
- Be conservative with compliance levels - require explicit coverage for "compliant"
- Limit to the top 10 most relevant control mappings
- Return ONLY the JSON object, no markdown or explanations"""


class DocumentAnalyzer:
    """Analyzes document text to extract policy information and control mappings."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.anthropic_api_key
        self._model = settings.claude_model

    @property
    def is_available(self) -> bool:
        """Check if Anthropic API key is configured."""
        return bool(self._api_key)

    async def analyze_document(
        self,
        text: str,
        filename: str,
        org_context: Optional[str] = None,
    ) -> PolicyAnalysisResult:
        """
        Analyze document text to determine policy content and control mappings.

        Args:
            text: Extracted document text
            filename: Original filename for context
            org_context: Optional organization context string

        Returns:
            PolicyAnalysisResult with analysis details
        """
        if not self.is_available:
            logger.warning("Anthropic API key not configured, skipping policy analysis")
            return PolicyAnalysisResult(is_policy=False, confidence=0.0)

        # Truncate text to avoid token limits (roughly 100k chars ~ 25k tokens)
        max_chars = 100_000
        truncated = text[:max_chars]
        if len(text) > max_chars:
            truncated += "\n\n[... document truncated for analysis ...]"

        user_message = f"Filename: {filename}\n\n"
        if org_context:
            user_message += f"Organization context: {org_context}\n\n"
        user_message += f"Document text:\n\n{truncated}"

        try:
            client = anthropic.AsyncAnthropic(api_key=self._api_key)
            response = await client.messages.create(
                model=self._model,
                max_tokens=4000,
                system=ANALYSIS_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": user_message,
                    }
                ],
            )

            # Parse the JSON response
            response_text = response.content[0].text.strip()

            # Handle potential markdown code block wrapping
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                # Remove first and last lines (```json and ```)
                response_text = "\n".join(lines[1:-1])

            data = json.loads(response_text)

            # Build control mappings
            controls = []
            for ctrl in data.get("controls_addressed", []):
                controls.append(
                    ControlMapping(
                        framework=ctrl.get("framework", "iso27001"),
                        identifier=ctrl.get("identifier", ""),
                        title=ctrl.get("title", ""),
                        compliance_level=ctrl.get(
                            "compliance_level", "partially_compliant"
                        ),
                        evidence=ctrl.get("evidence", ""),
                        gap=ctrl.get("gap"),
                    )
                )

            result = PolicyAnalysisResult(
                is_policy=data.get("is_policy", False),
                policy_type=data.get("policy_type"),
                title=data.get("title"),
                version=data.get("version"),
                effective_date=data.get("effective_date"),
                scope_summary=data.get("scope_summary"),
                controls_addressed=controls,
                confidence=data.get("confidence", 0.0),
            )

            logger.info(
                f"Document analysis for {filename}: is_policy={result.is_policy}, "
                f"controls={len(result.controls_addressed)}, "
                f"confidence={result.confidence}"
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse analysis response for {filename}: {e}")
            return PolicyAnalysisResult(is_policy=False, confidence=0.0)
        except Exception as e:
            logger.error(f"Document analysis failed for {filename}: {e}")
            return PolicyAnalysisResult(is_policy=False, confidence=0.0)
