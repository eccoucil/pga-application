"""Web Crawler package — CRAWL4AI-powered web intelligence extraction.

Re-exports the public API so consumers can use::

    from app.services.web_crawler import WebCrawlerAgent, get_web_crawler_agent
"""

from app.services.web_crawler.agent import (
    WebCrawlerAgent,
    get_web_crawler_agent,
    reset_web_crawler_agent,
)

__all__ = [
    "WebCrawlerAgent",
    "get_web_crawler_agent",
    "reset_web_crawler_agent",
]
