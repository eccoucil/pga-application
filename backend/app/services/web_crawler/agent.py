"""Slim orchestrator for web crawl intelligence extraction.

Coordinates sub-agents (crawl → parallel LLM extraction → store) without
containing any extraction logic itself.
"""

import asyncio
import logging
import time
from typing import Optional

import anthropic
from supabase import AsyncClient

from app.config import get_settings
from app.models.web_crawler import CrawlRequest, CrawlResult, PageData, SecurityContext
from app.services.web_crawler.asset_discovery import AssetDiscoveryAgent
from app.services.web_crawler.business_analyzer import BusinessContextAnalyzer
from app.services.web_crawler.confidence import calculate_confidence
from app.services.web_crawler.crawl_coordinator import CrawlCoordinator
from app.services.web_crawler.org_info_extractor import OrganizationInfoExtractor
from app.services.web_crawler.security_analyzer import (
    SecurityIndicatorExtractor,
    analyze_security,
)
from app.services.web_crawler.storage import StorageService

logger = logging.getLogger(__name__)

# Singleton state
_agent: Optional["WebCrawlerAgent"] = None
_lock = asyncio.Lock()


class WebCrawlerAgent:
    """Main web crawler agent that orchestrates sub-agents.

    Role: "Web Intelligence Extraction Specialist"
    Goal: Extract accurate, verifiable business intelligence with 95%+ confidence
    """

    def __init__(
        self,
        anthropic_client: anthropic.AsyncAnthropic,
        supabase_client: AsyncClient,
        *,
        crawl_coordinator: Optional[CrawlCoordinator] = None,
        business_analyzer: Optional[BusinessContextAnalyzer] = None,
        asset_agent: Optional[AssetDiscoveryAgent] = None,
        org_extractor: Optional[OrganizationInfoExtractor] = None,
        security_indicator_extractor: Optional[SecurityIndicatorExtractor] = None,
        storage: Optional[StorageService] = None,
    ) -> None:
        settings = get_settings()
        model = settings.claude_model

        # Sub-agents (injectable for testing)
        self.crawl_coordinator = crawl_coordinator or CrawlCoordinator(
            max_pages=settings.crawl4ai_max_pages,
            timeout=settings.crawl4ai_timeout,
        )
        self.business_analyzer = business_analyzer or BusinessContextAnalyzer(
            anthropic_client, model
        )
        self.asset_agent = asset_agent or AssetDiscoveryAgent(anthropic_client, model)
        self.org_extractor = org_extractor or OrganizationInfoExtractor(
            anthropic_client, model
        )
        self.security_indicator_extractor = (
            security_indicator_extractor
            or SecurityIndicatorExtractor(anthropic_client, model)
        )

        # Storage
        self.storage = storage or StorageService(supabase_client)

    async def crawl_domain(self, request: CrawlRequest, user_id: str) -> CrawlResult:
        """Main entry point: crawl domain and extract intelligence."""
        start_time = time.time()
        errors: list[str] = []

        self.crawl_coordinator.max_pages = request.max_pages

        # Phase 1: Crawl pages
        logger.info(f"Starting crawl of {request.web_domain}")
        try:
            pages: list[PageData] = await self.crawl_coordinator.crawl(
                request.web_domain
            )
        except Exception as e:
            logger.error(f"Crawl failed: {e}")
            errors.append(f"Crawl failed: {e!s}")
            pages = []

        if not pages:
            return CrawlResult(
                success=False,
                web_domain=request.web_domain,
                client_id=request.client_id,
                project_id=request.project_id,
                pages_crawled=0,
                total_words_analyzed=0,
                confidence_score=0.0,
                processing_time_ms=int((time.time() - start_time) * 1000),
                errors=errors or ["No pages could be crawled"],
            )

        total_words = sum(p.word_count for p in pages)
        logger.info(f"Crawled {len(pages)} pages, {total_words} words")

        # Phase 2: Parallel extraction (including security analysis)
        logger.info("Starting parallel extraction with sub-agents")
        business_context, assets, org_info = None, [], None
        security_context: Optional[SecurityContext] = None
        try:
            bc_result, ad_result, oi_result, sec_result = await asyncio.gather(
                self.business_analyzer.extract(pages),
                self.asset_agent.extract(pages, base_domain=request.web_domain),
                self.org_extractor.extract(pages),
                analyze_security(
                    request.web_domain,
                    pages,
                    indicator_extractor=self.security_indicator_extractor,
                ),
                return_exceptions=True,
            )
            if isinstance(bc_result, Exception):
                errors.append(f"Business context extraction failed: {bc_result}")
            else:
                business_context = bc_result
            if isinstance(ad_result, Exception):
                errors.append(f"Asset discovery failed: {ad_result}")
            else:
                assets = ad_result
            if isinstance(oi_result, Exception):
                errors.append(f"Organization info extraction failed: {oi_result}")
            else:
                org_info = oi_result
            if isinstance(sec_result, Exception):
                errors.append(f"Security analysis failed: {sec_result}")
            else:
                security_context = sec_result
        except Exception as e:
            logger.error(f"Extraction phase failed: {e}")
            errors.append(f"Extraction failed: {e!s}")

        # Phase 3: Confidence
        confidence = calculate_confidence(pages, business_context, assets, org_info)

        # Phase 4: Persist
        graph_company, graph_assets, attack_surface = None, [], None
        try:
            (
                graph_company,
                graph_assets,
                attack_surface,
            ) = await self.storage.store_in_neo4j(request, business_context, assets)
        except Exception as e:
            # Neo4j storage is non-critical — data is in Supabase
            logger.warning(f"Neo4j storage failed (non-critical): {e}")

        try:
            await self.storage.store_in_supabase(
                request=request,
                user_id=user_id,
                pages_crawled=len(pages),
                business_context=business_context,
                assets=assets,
                org_info=org_info,
                confidence_score=confidence.overall,
            )
        except Exception as e:
            logger.error(f"Supabase storage failed: {e}")
            errors.append(f"Database storage failed: {e!s}")

        return CrawlResult(
            success=len(errors) == 0,
            web_domain=request.web_domain,
            client_id=request.client_id,
            project_id=request.project_id,
            pages_crawled=len(pages),
            total_words_analyzed=total_words,
            business_context=business_context,
            digital_assets=assets,
            organization_info=org_info,
            confidence_score=confidence.overall,
            processing_time_ms=int((time.time() - start_time) * 1000),
            errors=errors,
            security_context=security_context,
            attack_surface=attack_surface,
            graph_company=graph_company,
            graph_assets=graph_assets,
        )


# =====================================================================
# Singleton factory (thread-safe via asyncio.Lock)
# =====================================================================


async def get_web_crawler_agent() -> WebCrawlerAgent:
    """Get or create the singleton ``WebCrawlerAgent``."""
    global _agent
    if _agent is not None:
        return _agent

    async with _lock:
        # Double-checked locking
        if _agent is not None:
            return _agent

        settings = get_settings()
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for web crawler agent")

        anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        from app.db.supabase import get_async_supabase_client_async

        supabase = await get_async_supabase_client_async()

        _agent = WebCrawlerAgent(
            anthropic_client=anthropic_client,
            supabase_client=supabase,
        )

    return _agent


def reset_web_crawler_agent() -> None:
    """Reset agent for testing."""
    global _agent
    _agent = None
