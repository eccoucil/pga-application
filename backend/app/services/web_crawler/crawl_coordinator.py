"""CRAWL4AI-based crawl coordinator with concurrent fetching.

Uses an ``asyncio.Semaphore`` to bound parallelism and a token-bucket rate
limiter to avoid hammering target servers.
"""

import asyncio
import logging
import time
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

from app.models.web_crawler import PageData
from app.services.web_crawler.constants import (
    CONCURRENT_CRAWL_LIMIT,
    CRAWL_RATE_LIMIT_PER_SEC,
    PAGE_TIMEOUT_SECONDS,
    WORD_COUNT_THRESHOLD,
)
from app.services.web_crawler.content_extractor import ContentExtractor

logger = logging.getLogger(__name__)


class _TokenBucket:
    """Simple async token-bucket rate limiter."""

    def __init__(self, rate: float) -> None:
        self._rate = rate
        self._tokens = 1.0
        self._max_tokens = rate  # burst = 1 second's worth
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            self._tokens = min(self._max_tokens, self._tokens + elapsed * self._rate)
            self._last = now
            if self._tokens < 1.0:
                wait = (1.0 - self._tokens) / self._rate
                await asyncio.sleep(wait)
                self._tokens = 0.0
                self._last = time.monotonic()
            else:
                self._tokens -= 1.0


class CrawlCoordinator:
    """Coordinates crawling strategy using CRAWL4AI with concurrency."""

    def __init__(
        self,
        max_pages: int,
        timeout: int,
        *,
        concurrency: int = CONCURRENT_CRAWL_LIMIT,
        rate_limit: float = CRAWL_RATE_LIMIT_PER_SEC,
    ) -> None:
        self.max_pages = max_pages
        self.timeout = timeout
        self.content_extractor = ContentExtractor()
        self._concurrency = concurrency
        self._rate_limit = rate_limit

    async def crawl(self, domain: str) -> list[PageData]:
        """Crawl *domain* using concurrent BFS and return extracted pages."""
        start_url = domain if domain.startswith("http") else f"https://{domain}"

        pages: list[PageData] = []
        visited: set[str] = set()
        to_visit: list[str] = [start_url]
        pages_lock = asyncio.Lock()

        sem = asyncio.Semaphore(self._concurrency)
        bucket = _TokenBucket(self._rate_limit)

        browser_config = BrowserConfig(headless=True, verbose=False)
        crawler_config = CrawlerRunConfig(
            word_count_threshold=WORD_COUNT_THRESHOLD,
            excluded_tags=["nav", "footer", "header", "script", "style"],
            exclude_external_links=False,
        )

        async def _fetch_one(
            crawler: AsyncWebCrawler, url: str, base_domain: str
        ) -> None:
            """Fetch a single URL, guarded by semaphore + rate limiter."""
            async with sem:
                await bucket.acquire()

                async with pages_lock:
                    if len(pages) >= self.max_pages:
                        return

                try:
                    result = await asyncio.wait_for(
                        crawler.arun(url, config=crawler_config),
                        timeout=PAGE_TIMEOUT_SECONDS,
                    )

                    if result.success and result.markdown:
                        page = self.content_extractor.extract(result.markdown, url)

                        async with pages_lock:
                            if len(pages) >= self.max_pages:
                                return
                            pages.append(page)

                            # Enqueue same-domain internal links
                            for link in page.links:
                                link_parsed = urlparse(link)
                                if (
                                    link_parsed.netloc == base_domain
                                    or link_parsed.netloc.endswith(f".{base_domain}")
                                ) and link not in visited:
                                    visited.add(link)
                                    to_visit.append(link)

                        logger.info(
                            f"Crawled {url}: {page.word_count} words, "
                            f"{len(page.links)} links"
                        )

                except asyncio.TimeoutError:
                    logger.warning(f"Timeout crawling {url}")
                except Exception as e:
                    logger.warning(f"Error crawling {url}: {e}")

        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                parsed_start = urlparse(start_url)
                base_domain = parsed_start.netloc

                while to_visit:
                    # Grab a batch of unvisited URLs
                    batch: list[str] = []
                    while to_visit and len(batch) < self._concurrency:
                        url = to_visit.pop(0)
                        if url not in visited:
                            visited.add(url)
                            batch.append(url)

                    if not batch:
                        break

                    # Check page limit before launching batch
                    async with pages_lock:
                        if len(pages) >= self.max_pages:
                            break

                    # Fetch batch concurrently
                    await asyncio.gather(
                        *(_fetch_one(crawler, url, base_domain) for url in batch)
                    )

        except Exception as e:
            logger.error(f"Crawler initialization error: {e}")

        return pages
