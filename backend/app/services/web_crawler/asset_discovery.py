"""Digital asset discovery via LLM.

Extends ``BaseLLMExtractor`` to find subdomains, portals, APIs, and
applications from crawled page content and link analysis.
"""

import logging
import re
from typing import Any
from urllib.parse import urlparse

from app.models.web_crawler import DigitalAsset, PageData
from app.services.web_crawler.base_extractor import BaseLLMExtractor
from app.services.web_crawler.constants import (
    ASSET_CONTENT_LIMIT,
    ASSET_MAX_TOKENS,
    ASSET_TYPE_MAP,
    DEFAULT_ASSET_TYPE,
    MAX_ASSET_PAGES,
    MAX_DOMAIN_LINKS,
)

logger = logging.getLogger(__name__)


class AssetDiscoveryAgent(BaseLLMExtractor):
    """Discovers digital assets from crawled pages using an LLM."""

    SYSTEM_PROMPT = (
        "You are a digital asset discovery specialist. Analyze web pages to "
        "identify digital assets such as subdomains, portals, APIs, and applications.\n\n"
        "For each asset found:\n"
        "1. Identify the URL\n"
        '2. Classify the type: "subdomain", "portal", "api", "application", or "website"\n'
        "3. Describe its purpose based on explicit content\n"
        "4. Note any technology hints (frameworks, languages)\n"
        "5. Quote the source text\n\n"
        "Return a JSON array of assets:\n"
        "[\n"
        "    {\n"
        '        "asset_type": "subdomain|portal|api|application|website",\n'
        '        "url": "https://...",\n'
        '        "description": "what this asset does",\n'
        '        "purpose": "its function or null",\n'
        '        "technology_hints": ["React", "Python", etc.],\n'
        '        "grounding_source": "quoted text proving this asset exists"\n'
        "    }\n"
        "]\n\n"
        "If no assets found, return: []\n"
        "Only include assets with explicit evidence. Do NOT fabricate URLs."
    )

    # ------------------------------------------------------------------
    # Template hooks
    # ------------------------------------------------------------------

    def _prepare_content(self, pages: list[PageData], **kwargs: Any) -> str:
        base_domain: str = kwargs.get("base_domain", "")

        # Collect unique links
        all_links: set[str] = set()
        for page in pages:
            all_links.update(page.links)
            all_links.update(re.findall(r'https?://[^\s<>"]+', page.content))

        # Filter to same domain or subdomains
        domain_links = [
            link
            for link in all_links
            if base_domain in urlparse(link).netloc or base_domain in link
        ]

        combined = f"Base domain: {base_domain}\n\nFound URLs:\n"
        combined += "\n".join(domain_links[:MAX_DOMAIN_LINKS])
        combined += "\n\n---PAGE CONTENT---\n\n"
        combined += "\n\n".join(
            p.content[:ASSET_CONTENT_LIMIT] for p in pages[:MAX_ASSET_PAGES]
        )
        return f"Discover digital assets from:\n\n{combined}"

    def _parse_result(
        self, data: list, pages: list[PageData], **kwargs: Any
    ) -> list[DigitalAsset]:
        assets: list[DigitalAsset] = []
        for item in data:
            try:
                asset_type_str = item.get("asset_type", "website").lower()
                asset_type = ASSET_TYPE_MAP.get(asset_type_str, DEFAULT_ASSET_TYPE)
                assets.append(
                    DigitalAsset(
                        asset_type=asset_type,
                        url=item.get("url", ""),
                        description=item.get("description", ""),
                        purpose=item.get("purpose"),
                        technology_hints=item.get("technology_hints") or [],
                        grounding_source=item.get("grounding_source", ""),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse asset: {e}")
        return assets

    def _empty_result(self) -> list:
        return []

    def _max_tokens(self) -> int:
        return ASSET_MAX_TOKENS

    def _expect_array(self) -> bool:
        return True
