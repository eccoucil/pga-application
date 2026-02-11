"""Business context extraction via LLM.

Extends ``BaseLLMExtractor`` — only content preparation and result parsing
are custom; the API call, JSON extraction, and error handling are inherited.
"""

from typing import Any, Optional

from app.models.web_crawler import BusinessContext, PageData
from app.services.web_crawler.base_extractor import BaseLLMExtractor
from app.services.web_crawler.constants import (
    BUSINESS_CONTENT_LIMIT,
    BUSINESS_MAX_TOKENS,
    MAX_ANALYSIS_PAGES,
)


class BusinessContextAnalyzer(BaseLLMExtractor):
    """Analyzes crawled pages to extract business context."""

    SYSTEM_PROMPT = (
        "You are a precise web content analyst. Extract ONLY information "
        "explicitly stated in the provided web page content. NEVER infer, "
        "assume, or fabricate information.\n\n"
        "For each extraction:\n"
        "1. Quote the exact text from the source\n"
        "2. If information is not found, return null for that field\n"
        "3. Your responses must be 100% verifiable from the source material\n\n"
        "You MUST return a valid JSON object with this exact structure:\n"
        "{\n"
        '    "company_name": "string or null",\n'
        '    "industry": "string or null",\n'
        '    "description": "string or null",\n'
        '    "mission_statement": "string or null",\n'
        '    "key_services": ["array of strings"],\n'
        '    "target_audience": "string or null",\n'
        '    "grounding_source": "URL + exact quoted text that proves your extractions"\n'
        "}\n\n"
        "If you cannot find enough information for a confident extraction, return:\n"
        '{"error": "insufficient_data", "reason": "explanation"}'
    )

    # ------------------------------------------------------------------
    # Template hooks
    # ------------------------------------------------------------------

    def _prepare_content(self, pages: list[PageData], **kwargs: Any) -> str:
        combined = "\n\n---PAGE BREAK---\n\n".join(
            f"URL: {p.url}\n\n{p.content[:BUSINESS_CONTENT_LIMIT]}"
            for p in pages[:MAX_ANALYSIS_PAGES]
        )
        return f"Extract business context from these web pages:\n\n{combined}"

    def _parse_result(
        self, data: dict, pages: list[PageData], **kwargs: Any
    ) -> Optional[BusinessContext]:
        if "error" in data:
            return None

        return BusinessContext(
            company_name=data.get("company_name") or "Unknown",
            industry=data.get("industry") or "Unknown",
            description=data.get("description") or "",
            mission_statement=data.get("mission_statement"),
            key_services=data.get("key_services") or [],
            target_audience=data.get("target_audience"),
            grounding_source=data.get("grounding_source") or pages[0].url,
        )

    def _empty_result(self) -> None:
        return None

    def _max_tokens(self) -> int:
        return BUSINESS_MAX_TOKENS
