"""Backward-compatibility shim.

The web crawler has been refactored into ``app.services.web_crawler`` package.
This module re-exports the public API so existing consumers (e.g.
``assessment_orchestrator.py`` and tests) continue to work without changes.
"""

from app.services.web_crawler import (  # noqa: F401
    WebCrawlerAgent,
    get_web_crawler_agent,
    reset_web_crawler_agent,
)
