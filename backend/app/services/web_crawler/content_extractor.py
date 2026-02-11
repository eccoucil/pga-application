"""Pure-Python HTML/markdown → PageData extractor.

No LLM calls — uses regex to pull titles, links, and word counts.
"""

import re
from datetime import datetime

from app.models.web_crawler import PageData
from app.services.web_crawler.constants import MAX_CONTENT_LENGTH, MAX_LINKS_PER_PAGE


class ContentExtractor:
    """Extracts clean text content from crawled pages."""

    def extract(self, raw_content: str, url: str) -> PageData:
        """Extract clean content from raw HTML/markdown."""
        words = raw_content.split()
        word_count = len(words)

        links = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', raw_content)
        unique_links = list(set(links))

        title_match = re.search(r"^#\s*(.+)$", raw_content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else None

        return PageData(
            url=url,
            title=title,
            content=raw_content[:MAX_CONTENT_LENGTH],
            word_count=word_count,
            links=unique_links[:MAX_LINKS_PER_PAGE],
            crawl_timestamp=datetime.utcnow(),
        )
