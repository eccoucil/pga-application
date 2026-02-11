"""Organization info extraction via LLM.

Extends ``BaseLLMExtractor`` to extract contact details, certifications,
and partnerships from crawled pages.
"""

from typing import Any, Optional

from app.models.web_crawler import OrganizationInfo, PageData, SocialMediaLink
from app.services.web_crawler.base_extractor import BaseLLMExtractor
from app.services.web_crawler.constants import (
    MAX_ANALYSIS_PAGES,
    ORG_CONTENT_LIMIT,
    ORG_MAX_TOKENS,
)


class OrganizationInfoExtractor(BaseLLMExtractor):
    """Extracts organization contact & certification info."""

    SYSTEM_PROMPT = (
        "You are an organization information specialist. Extract contact "
        "information, certifications, and partnerships from web pages.\n\n"
        "Extract ONLY explicitly stated information. Return JSON:\n"
        "{\n"
        '    "headquarters_location": "address or null",\n'
        '    "contact_email": "email or null",\n'
        '    "contact_phone": "phone or null",\n'
        '    "social_media_links": [{"platform": "LinkedIn", "url": "..."}],\n'
        '    "certifications": ["ISO 27001", "SOC 2", etc.],\n'
        '    "partnerships": ["Partner Name", etc.],\n'
        '    "grounding_source": "URLs and quoted text proving extractions"\n'
        "}\n\n"
        "If no information found, return empty values (null, []).\n"
        "NEVER fabricate contact information - only extract what is explicitly shown."
    )

    # ------------------------------------------------------------------
    # Template hooks
    # ------------------------------------------------------------------

    def _prepare_content(self, pages: list[PageData], **kwargs: Any) -> str:
        # Prioritise contact/about pages
        priority: list[PageData] = []
        other: list[PageData] = []
        for p in pages:
            lower_url = p.url.lower()
            if any(
                kw in lower_url
                for kw in ("contact", "about", "team", "company", "info")
            ):
                priority.append(p)
            else:
                other.append(p)

        pages_to_analyze = (priority + other)[:MAX_ANALYSIS_PAGES]
        combined = "\n\n---PAGE BREAK---\n\n".join(
            f"URL: {p.url}\n\n{p.content[:ORG_CONTENT_LIMIT]}" for p in pages_to_analyze
        )
        return f"Extract organization info from:\n\n{combined}"

    def _parse_result(
        self, data: dict, pages: list[PageData], **kwargs: Any
    ) -> Optional[OrganizationInfo]:
        social_links: list[SocialMediaLink] = []
        for link in data.get("social_media_links") or []:
            if isinstance(link, dict):
                social_links.append(
                    SocialMediaLink(
                        platform=link.get("platform", "Unknown"),
                        url=link.get("url", ""),
                    )
                )

        return OrganizationInfo(
            headquarters_location=data.get("headquarters_location"),
            contact_email=data.get("contact_email"),
            contact_phone=data.get("contact_phone"),
            social_media_links=social_links,
            certifications=data.get("certifications") or [],
            partnerships=data.get("partnerships") or [],
            grounding_source=data.get("grounding_source") or pages[0].url,
        )

    def _empty_result(self) -> None:
        return None

    def _max_tokens(self) -> int:
        return ORG_MAX_TOKENS
