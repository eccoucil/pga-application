"""Tests for app.services.web_crawler.agent (orchestrator)."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.web_crawler import (
    BusinessContext,
    CrawlRequest,
    DigitalAsset,
    GraphAsset,
    GraphCompany,
    OrganizationInfo,
    PageData,
    SecurityContext,
)
from app.services.web_crawler.agent import WebCrawlerAgent


def _make_page(url: str = "https://example.com", word_count: int = 200) -> PageData:
    return PageData(
        url=url,
        title="Test Page",
        content="word " * word_count,
        word_count=word_count,
        links=[],
        crawl_timestamp=datetime.utcnow(),
    )


def _make_request() -> CrawlRequest:
    return CrawlRequest(
        web_domain="example.com",
        client_id="client-123",
        project_id="project-456",
        max_pages=5,
    )


def _make_business_context() -> BusinessContext:
    return BusinessContext(
        company_name="Acme Corp",
        industry="Technology",
        description="A tech company",
        key_services=["SaaS"],
        grounding_source="https://example.com — 'We are a tech company'",
    )


def _make_agent(
    pages: list[PageData] | None = None,
    business_context: BusinessContext | None = None,
    assets: list[DigitalAsset] | None = None,
    org_info: OrganizationInfo | None = None,
) -> WebCrawlerAgent:
    """Build a WebCrawlerAgent with fully mocked sub-agents."""
    mock_anthropic = MagicMock()
    mock_neo4j = MagicMock()
    mock_supabase = MagicMock()

    # Mock crawl coordinator
    crawl_coordinator = MagicMock()
    crawl_coordinator.crawl = AsyncMock(
        return_value=pages if pages is not None else [_make_page()]
    )

    # Mock LLM extractors
    business_analyzer = MagicMock()
    business_analyzer.extract = AsyncMock(return_value=business_context)

    asset_agent = MagicMock()
    asset_agent.extract = AsyncMock(return_value=assets or [])

    org_extractor = MagicMock()
    org_extractor.extract = AsyncMock(return_value=org_info)

    # Mock security indicator extractor
    security_indicator_extractor = MagicMock()
    security_indicator_extractor.extract = AsyncMock(return_value=[])

    # Mock storage
    storage = MagicMock()
    storage.store_in_neo4j = AsyncMock(return_value=(None, [], None))
    storage.store_in_supabase = AsyncMock()

    with patch("app.services.web_crawler.agent.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            claude_model="test-model",
            crawl4ai_max_pages=10,
            crawl4ai_timeout=60,
        )
        agent = WebCrawlerAgent(
            anthropic_client=mock_anthropic,
            neo4j_service=mock_neo4j,
            supabase_client=mock_supabase,
            crawl_coordinator=crawl_coordinator,
            business_analyzer=business_analyzer,
            asset_agent=asset_agent,
            org_extractor=org_extractor,
            security_indicator_extractor=security_indicator_extractor,
            storage=storage,
        )

    return agent


@pytest.fixture(autouse=True)
def _mock_analyze_security():
    """Patch analyze_security for all tests to avoid network calls."""
    with patch(
        "app.services.web_crawler.agent.analyze_security",
        new_callable=AsyncMock,
        return_value=SecurityContext(),
    ):
        yield


@pytest.mark.asyncio
class TestWebCrawlerAgent:
    async def test_successful_crawl(self):
        """Happy path: crawl succeeds with all extractions."""
        agent = _make_agent(
            pages=[_make_page(), _make_page("https://example.com/about")],
            business_context=_make_business_context(),
            assets=[
                DigitalAsset(
                    asset_type="portal",
                    url="https://portal.example.com",
                    description="Customer portal",
                    grounding_source="evidence",
                )
            ],
            org_info=OrganizationInfo(grounding_source="org evidence"),
        )

        result = await agent.crawl_domain(_make_request(), "user-1")

        assert result.success is True
        assert result.pages_crawled == 2
        assert result.business_context is not None
        assert result.business_context.company_name == "Acme Corp"
        assert len(result.digital_assets) == 1
        assert result.organization_info is not None
        assert result.confidence_score > 0.0
        assert result.security_context is not None

    async def test_no_pages_returns_failure(self):
        """When crawl returns no pages, result is failure."""
        agent = _make_agent(pages=[])
        result = await agent.crawl_domain(_make_request(), "user-1")

        assert result.success is False
        assert result.pages_crawled == 0
        assert "No pages could be crawled" in result.errors

    async def test_extraction_exceptions_handled(self):
        """If an extractor raises, it's logged but crawl continues."""
        agent = _make_agent(pages=[_make_page()])
        agent.business_analyzer.extract = AsyncMock(
            side_effect=RuntimeError("LLM boom")
        )

        result = await agent.crawl_domain(_make_request(), "user-1")

        assert result.business_context is None
        assert any("Business context" in e for e in result.errors)
        assert result.pages_crawled == 1

    async def test_storage_errors_recorded(self):
        """Storage failures are appended to errors, not raised."""
        agent = _make_agent(pages=[_make_page()])
        agent.storage.store_in_neo4j = AsyncMock(
            side_effect=RuntimeError("Neo4j down")
        )
        agent.storage.store_in_supabase = AsyncMock(
            side_effect=RuntimeError("Supabase down")
        )

        result = await agent.crawl_domain(_make_request(), "user-1")

        assert result.success is False
        assert any("Graph storage" in e for e in result.errors)
        assert any("Database storage" in e for e in result.errors)

    async def test_processing_time_recorded(self):
        """Processing time is always a non-negative integer."""
        agent = _make_agent()
        result = await agent.crawl_domain(_make_request(), "user-1")
        assert result.processing_time_ms >= 0

    async def test_max_pages_forwarded_to_coordinator(self):
        """The request's max_pages overrides the coordinator default."""
        agent = _make_agent()
        request = _make_request()
        request.max_pages = 3
        await agent.crawl_domain(request, "user-1")
        assert agent.crawl_coordinator.max_pages == 3
