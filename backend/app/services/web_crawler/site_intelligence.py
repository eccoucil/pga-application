"""Site intelligence: robots.txt and sitemap.xml parsing.

Pre-crawl analysis that discovers additional URLs and respects robots rules.
No LLM calls — pure HTTP + parsing.
"""

import logging
import re
from typing import Optional
from urllib.parse import urljoin

import httpx

from app.models.web_crawler import RobotsData

logger = logging.getLogger(__name__)

_TIMEOUT = 10  # seconds for robots/sitemap fetches


async def fetch_robots_data(domain: str) -> Optional[RobotsData]:
    """Fetch and parse robots.txt for *domain*.

    Returns ``None`` if robots.txt is inaccessible.
    """
    base_url = f"https://{domain}" if not domain.startswith("http") else domain
    robots_url = urljoin(base_url.rstrip("/") + "/", "robots.txt")

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(robots_url)
            if resp.status_code != 200:
                return None
            return _parse_robots_txt(resp.text)
    except Exception as e:
        logger.warning(f"Failed to fetch robots.txt for {domain}: {e}")
        return None


def _parse_robots_txt(text: str) -> RobotsData:
    """Parse robots.txt content into structured data."""
    allowed: list[str] = []
    disallowed: list[str] = []
    sitemaps: list[str] = []
    crawl_delay: Optional[float] = None

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        lower = line.lower()
        if lower.startswith("allow:"):
            path = line.split(":", 1)[1].strip()
            if path:
                allowed.append(path)
        elif lower.startswith("disallow:"):
            path = line.split(":", 1)[1].strip()
            if path:
                disallowed.append(path)
        elif lower.startswith("sitemap:"):
            url = line.split(":", 1)[1].strip()
            if url:
                sitemaps.append(url)
        elif lower.startswith("crawl-delay:"):
            try:
                crawl_delay = float(line.split(":", 1)[1].strip())
            except ValueError:
                pass

    return RobotsData(
        allowed_paths=allowed,
        disallowed_paths=disallowed,
        sitemaps=sitemaps,
        crawl_delay=crawl_delay,
    )


async def fetch_sitemap_urls(sitemap_url: str, *, max_urls: int = 100) -> list[str]:
    """Fetch a sitemap and extract up to *max_urls* page URLs.

    Handles both XML sitemaps and sitemap index files (recursing one level).
    """
    urls: list[str] = []

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(sitemap_url)
            if resp.status_code != 200:
                return urls

            content = resp.text

            # Check for sitemap index (contains <sitemap> elements)
            sub_sitemaps = re.findall(r"<sitemap>\s*<loc>\s*(.*?)\s*</loc>", content)
            if sub_sitemaps:
                for sub_url in sub_sitemaps[:5]:  # limit recursion
                    sub_urls = await fetch_sitemap_urls(
                        sub_url, max_urls=max_urls - len(urls)
                    )
                    urls.extend(sub_urls)
                    if len(urls) >= max_urls:
                        break
                return urls[:max_urls]

            # Regular sitemap — extract <loc> URLs
            locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", content)
            urls.extend(locs[:max_urls])

    except Exception as e:
        logger.warning(f"Failed to fetch sitemap {sitemap_url}: {e}")

    return urls[:max_urls]
