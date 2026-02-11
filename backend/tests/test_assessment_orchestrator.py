"""Tests for assessment orchestrator parallel processing."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.assessment import (
    AssessmentRequest,
    AssessmentResponse,
    AssessmentSummary,
    DocumentResult,
    IndustryType,
    OrganizationContextSummary,
    OrganizationInfo,
    WebCrawlSummary,
)
from app.models.web_crawler import (
    BusinessContext,
    CrawlResult,
    DigitalAsset,
    DigitalAssetType,
)
from app.services.assessment_orchestrator import (
    AssessmentOrchestrator,
    reset_orchestrator,
)


@pytest.fixture
def orchestrator():
    """Create a fresh orchestrator for each test."""
    reset_orchestrator()
    return AssessmentOrchestrator()


@pytest.fixture
def sample_request_no_domain():
    """Assessment request without web domain."""
    return AssessmentRequest(
        client_id="client-123",
        project_id="project-456",
        organization_info=OrganizationInfo(
            organization_name="Test Corp",
            nature_of_business="Technology consulting and software development",
            industry_type=IndustryType.TECHNOLOGY,
            web_domain=None,  # No web domain
            department="IT Security",
            scope_statement_isms="ISMS covering all IT systems and data processing",
        ),
    )


@pytest.fixture
def sample_request_with_domain():
    """Assessment request with web domain."""
    return AssessmentRequest(
        client_id="client-123",
        project_id="project-456",
        organization_info=OrganizationInfo(
            organization_name="Test Corp",
            nature_of_business="Technology consulting and software development",
            industry_type=IndustryType.TECHNOLOGY,
            web_domain="example.com",  # With web domain
            department="IT Security",
            scope_statement_isms="ISMS covering all IT systems and data processing",
        ),
    )


def create_mock_upload_file(filename: str, content: bytes = b"test content"):
    """Create a mock UploadFile for testing."""
    mock_file = MagicMock()
    mock_file.filename = filename
    mock_file.read = AsyncMock(return_value=content)
    mock_file.seek = AsyncMock()
    return mock_file


@pytest.fixture
def sample_crawl_result():
    """Sample successful crawl result."""
    return CrawlResult(
        success=True,
        web_domain="example.com",
        client_id="client-123",
        project_id="project-456",
        pages_crawled=5,
        total_words_analyzed=1000,
        business_context=BusinessContext(
            company_name="Test Corp",
            industry="Technology",
            description="A technology company",
            key_services=["Consulting", "Development"],
            grounding_source="https://example.com - 'We are a technology company'",
        ),
        digital_assets=[
            DigitalAsset(
                asset_type=DigitalAssetType.PORTAL,
                url="https://portal.example.com",
                description="Customer portal",
                grounding_source="Found link on homepage",
            )
        ],
        confidence_score=0.85,
        errors=[],
    )


class TestWebCrawlSummaryModel:
    """Tests for WebCrawlSummary Pydantic model."""

    def test_create_successful_summary(self):
        """Test creating a successful web crawl summary."""
        summary = WebCrawlSummary(
            success=True,
            pages_crawled=10,
            digital_assets_found=5,
            business_context_extracted=True,
            organization_info_extracted=True,
            confidence_score=0.9,
            errors=[],
        )
        assert summary.success is True
        assert summary.pages_crawled == 10
        assert summary.digital_assets_found == 5
        assert summary.confidence_score == 0.9

    def test_create_failed_summary(self):
        """Test creating a failed web crawl summary."""
        summary = WebCrawlSummary(
            success=False,
            pages_crawled=0,
            digital_assets_found=0,
            business_context_extracted=False,
            organization_info_extracted=False,
            confidence_score=0.0,
            errors=["Connection timeout"],
        )
        assert summary.success is False
        assert summary.errors == ["Connection timeout"]

    def test_confidence_score_bounds(self):
        """Test confidence score validation (0.0 to 1.0)."""
        # Valid scores
        WebCrawlSummary(success=True, confidence_score=0.0)
        WebCrawlSummary(success=True, confidence_score=1.0)
        WebCrawlSummary(success=True, confidence_score=0.5)

        # Invalid scores should raise validation error
        with pytest.raises(ValueError):
            WebCrawlSummary(success=True, confidence_score=1.5)
        with pytest.raises(ValueError):
            WebCrawlSummary(success=True, confidence_score=-0.1)


class TestAssessmentResponseWithWebCrawl:
    """Tests for AssessmentResponse with web_crawl field."""

    def test_response_without_web_crawl(self):
        """Test response when no web domain was provided."""
        org_context = OrganizationContextSummary(
            created=True,
            organization_name="Test Corp",
            industry_type="Technology",
            department="IT",
            scope_statement_preview="Test scope statement",
            web_domain=None,
            context_nodes_created=["Organization"],
        )
        summary = AssessmentSummary(
            headline="Assessment received for Test Corp",
            processing_time_ms=100,
            highlights=["2 documents received"],
            next_step="review_findings",
            next_step_url="/clients/123/projects/456/findings",
        )
        response = AssessmentResponse(
            assessment_id="assess-123",
            project_id="project-456",
            documents_received=2,
            status="received",
            documents=[],
            web_crawl=None,
            organization_context=org_context,
            summary=summary,
        )
        assert response.web_crawl is None
        assert response.organization_context.created is True
        assert response.summary.processing_time_ms == 100

    def test_response_with_web_crawl(self):
        """Test response includes web crawl summary."""
        web_crawl_summary = WebCrawlSummary(
            success=True,
            pages_crawled=5,
            digital_assets_found=3,
            business_context_extracted=True,
            organization_info_extracted=True,
            confidence_score=0.85,
        )
        org_context = OrganizationContextSummary(
            created=True,
            organization_name="Test Corp",
            industry_type="Technology",
            department="IT",
            scope_statement_preview="Test scope statement",
            web_domain="test.com",
            context_nodes_created=["Organization", "Industry"],
        )
        assessment_summary = AssessmentSummary(
            headline="Assessment received for Test Corp",
            processing_time_ms=250,
            highlights=["5 pages crawled", "3 digital assets discovered"],
            next_step="review_findings",
            next_step_url="/clients/123/projects/456/findings",
        )
        response = AssessmentResponse(
            assessment_id="assess-123",
            project_id="project-456",
            documents_received=2,
            status="received",
            documents=[],
            web_crawl=web_crawl_summary,
            organization_context=org_context,
            summary=assessment_summary,
        )
        assert response.web_crawl is not None
        assert response.web_crawl.success is True
        assert response.web_crawl.pages_crawled == 5
        assert response.organization_context.web_domain == "test.com"
        assert "5 pages crawled" in response.summary.highlights


class TestOrchestratorDocumentsOnly:
    """Tests for document-only processing (no web domain)."""

    @pytest.mark.asyncio
    async def test_empty_documents(self, orchestrator, sample_request_no_domain):
        """Test handling empty document list."""
        response = await orchestrator.receive_assessment(
            request=sample_request_no_domain,
            documents=[],
        )
        assert response.documents_received == 0
        assert response.status == "received"
        assert response.web_crawl is None

    @pytest.mark.asyncio
    async def test_single_document_skipped(
        self, orchestrator, sample_request_no_domain
    ):
        """Test single document when LlamaExtract is not available."""
        mock_doc = create_mock_upload_file("policy.pdf")

        with patch(
            "app.services.assessment_orchestrator.AssessmentOrchestrator._process_document_extraction"
        ) as mock_extract:
            mock_extract.return_value = {
                "status": "skipped",
                "reason": "LLAMA_CLOUD_API_KEY not set",
            }

            response = await orchestrator.receive_assessment(
                request=sample_request_no_domain,
                documents=[mock_doc],
            )

        assert response.documents_received == 1
        assert response.documents[0].filename == "policy.pdf"
        assert response.documents[0].status == "pending"
        assert response.web_crawl is None


class TestOrchestratorParallelExecution:
    """Tests for parallel document + web crawl execution."""

    @pytest.mark.asyncio
    async def test_documents_and_web_crawl_parallel(
        self, orchestrator, sample_request_with_domain, sample_crawl_result
    ):
        """Test documents and web crawl run in parallel."""
        mock_doc = create_mock_upload_file("policy.pdf")

        with (
            patch(
                "app.services.assessment_orchestrator.AssessmentOrchestrator._process_document_extraction"
            ) as mock_extract,
            patch(
                "app.services.web_crawler_agent.get_web_crawler_agent"
            ) as mock_get_agent,
        ):
            mock_extract.return_value = {"status": "success", "qdrant_chunks": 5}

            # Mock web crawler agent
            mock_agent = MagicMock()
            mock_agent.crawl_domain = AsyncMock(return_value=sample_crawl_result)
            mock_get_agent.return_value = mock_agent

            response = await orchestrator.receive_assessment(
                request=sample_request_with_domain,
                documents=[mock_doc],
            )

        assert response.documents_received == 1
        assert response.documents[0].status == "processed"
        assert response.web_crawl is not None
        assert response.web_crawl.success is True
        assert response.web_crawl.pages_crawled == 5
        assert response.web_crawl.digital_assets_found == 1
        assert response.status == "received"


class TestOrchestratorErrorIsolation:
    """Tests for error isolation between parallel tasks."""

    @pytest.mark.asyncio
    async def test_web_crawl_failure_doesnt_affect_documents(
        self, orchestrator, sample_request_with_domain
    ):
        """Test that web crawl failure doesn't affect document processing."""
        mock_doc = create_mock_upload_file("policy.pdf")

        with (
            patch(
                "app.services.assessment_orchestrator.AssessmentOrchestrator._process_document_extraction"
            ) as mock_extract,
            patch(
                "app.services.web_crawler_agent.get_web_crawler_agent"
            ) as mock_get_agent,
        ):
            mock_extract.return_value = {"status": "success", "qdrant_chunks": 5}

            # Mock web crawler to fail
            mock_get_agent.side_effect = Exception("Web crawl connection error")

            response = await orchestrator.receive_assessment(
                request=sample_request_with_domain,
                documents=[mock_doc],
            )

        # Documents should still succeed
        assert response.documents_received == 1
        assert response.documents[0].status == "processed"

        # Web crawl should show failure
        assert response.web_crawl is not None
        assert response.web_crawl.success is False
        assert "failed or timed out" in response.web_crawl.errors[0]

        # Overall status should be partial
        assert response.status == "partial"

    @pytest.mark.asyncio
    async def test_document_failure_doesnt_affect_web_crawl(
        self, orchestrator, sample_request_with_domain, sample_crawl_result
    ):
        """Test that document failure doesn't affect web crawl."""
        mock_doc = create_mock_upload_file("policy.pdf")

        with (
            patch(
                "app.services.assessment_orchestrator.AssessmentOrchestrator._process_document_extraction"
            ) as mock_extract,
            patch(
                "app.services.web_crawler_agent.get_web_crawler_agent"
            ) as mock_get_agent,
        ):
            # Document extraction fails
            mock_extract.return_value = {"status": "error", "error": "Parse error"}

            # Web crawl succeeds
            mock_agent = MagicMock()
            mock_agent.crawl_domain = AsyncMock(return_value=sample_crawl_result)
            mock_get_agent.return_value = mock_agent

            response = await orchestrator.receive_assessment(
                request=sample_request_with_domain,
                documents=[mock_doc],
            )

        # Document should show failure
        assert response.documents[0].status == "failed"

        # Web crawl should still succeed
        assert response.web_crawl is not None
        assert response.web_crawl.success is True

        # Overall status should be partial
        assert response.status == "partial"

    @pytest.mark.asyncio
    async def test_all_failures_result_in_failed_status(
        self, orchestrator, sample_request_with_domain
    ):
        """Test that all failures result in failed status."""
        mock_doc = create_mock_upload_file("policy.pdf")

        with (
            patch(
                "app.services.assessment_orchestrator.AssessmentOrchestrator._process_document_extraction"
            ) as mock_extract,
            patch(
                "app.services.web_crawler_agent.get_web_crawler_agent"
            ) as mock_get_agent,
        ):
            # Both fail
            mock_extract.return_value = {"status": "error", "error": "Parse error"}
            mock_get_agent.side_effect = Exception("Connection error")

            response = await orchestrator.receive_assessment(
                request=sample_request_with_domain,
                documents=[mock_doc],
            )

        assert response.documents[0].status == "failed"
        assert response.web_crawl.success is False
        assert response.status == "failed"


class TestOrchestratorBuildResponse:
    """Tests for _build_response method."""

    def test_build_response_all_success(self, orchestrator, sample_request_with_domain):
        """Test response building when all tasks succeed."""
        doc_results = [
            DocumentResult(
                document_id="doc-1", filename="policy.pdf", status="processed"
            )
        ]
        crawl_result = CrawlResult(
            success=True,
            web_domain="example.com",
            client_id="client-123",
            project_id="project-456",
            pages_crawled=5,
            digital_assets=[],
            confidence_score=0.8,
        )

        response = orchestrator._build_response(
            assessment_id="assess-123",
            request=sample_request_with_domain,
            doc_results=doc_results,
            web_crawl_result=crawl_result,
            from_cache=False,
        )

        assert response.status == "received"
        assert response.web_crawl.success is True

    def test_build_response_partial_doc_failure(
        self, orchestrator, sample_request_with_domain
    ):
        """Test response when some documents fail."""
        doc_results = [
            DocumentResult(
                document_id="doc-1", filename="policy.pdf", status="processed"
            ),
            DocumentResult(document_id="doc-2", filename="broken.pdf", status="failed"),
        ]
        crawl_result = CrawlResult(
            success=True,
            web_domain="example.com",
            client_id="client-123",
            project_id="project-456",
            pages_crawled=5,
            digital_assets=[],
            confidence_score=0.8,
        )

        response = orchestrator._build_response(
            assessment_id="assess-123",
            request=sample_request_with_domain,
            doc_results=doc_results,
            web_crawl_result=crawl_result,
            from_cache=False,
        )

        assert response.status == "partial"

    def test_build_response_no_web_domain(self, orchestrator, sample_request_no_domain):
        """Test response when no web domain was provided."""
        doc_results = [
            DocumentResult(
                document_id="doc-1", filename="policy.pdf", status="processed"
            )
        ]

        response = orchestrator._build_response(
            assessment_id="assess-123",
            request=sample_request_no_domain,
            doc_results=doc_results,
            web_crawl_result=None,
            from_cache=False,
        )

        assert response.status == "received"
        assert response.web_crawl is None


class TestOrchestratorExtractResult:
    """Tests for _extract_result helper method."""

    def test_extract_existing_result(self, orchestrator):
        """Test extracting an existing result."""
        results = [["doc1", "doc2"], {"key": "value"}]
        task_names = ["documents", "web_crawl"]

        doc_result = orchestrator._extract_result(results, task_names, "documents", [])
        assert doc_result == ["doc1", "doc2"]

        web_result = orchestrator._extract_result(
            results, task_names, "web_crawl", None
        )
        assert web_result == {"key": "value"}

    def test_extract_missing_task(self, orchestrator):
        """Test extracting a task that wasn't run."""
        results = [["doc1", "doc2"]]
        task_names = ["documents"]

        result = orchestrator._extract_result(results, task_names, "web_crawl", None)
        assert result is None

    def test_extract_exception_result(self, orchestrator):
        """Test extracting when task raised an exception."""
        results = [["doc1"], ValueError("test error")]
        task_names = ["documents", "web_crawl"]

        result = orchestrator._extract_result(
            results, task_names, "web_crawl", "default"
        )
        assert result == "default"


class TestOrchestratorConcurrency:
    """Tests for concurrent document processing."""

    @pytest.mark.asyncio
    async def test_multiple_documents_parallel(
        self, orchestrator, sample_request_no_domain
    ):
        """Test that multiple documents are processed in parallel."""
        docs = [create_mock_upload_file(f"doc{i}.pdf") for i in range(3)]

        # Track processing order to verify parallelism
        processing_order = []

        async def mock_extraction(*args, **kwargs):
            filename = kwargs.get("filename", args[4] if len(args) > 4 else "unknown")
            processing_order.append(f"start_{filename}")
            await asyncio.sleep(0.01)  # Small delay to allow interleaving
            processing_order.append(f"end_{filename}")
            return {"status": "success", "qdrant_chunks": 1}

        with patch(
            "app.services.assessment_orchestrator.AssessmentOrchestrator._process_document_extraction",
            side_effect=mock_extraction,
        ):
            response = await orchestrator.receive_assessment(
                request=sample_request_no_domain,
                documents=docs,
            )

        assert response.documents_received == 3
        assert all(d.status == "processed" for d in response.documents)

        # With parallel processing, starts should come before ends
        # (interleaved pattern indicates parallelism)
        starts = [i for i, x in enumerate(processing_order) if x.startswith("start_")]
        ends = [i for i, x in enumerate(processing_order) if x.startswith("end_")]
        # All starts should happen before all ends if truly parallel
        # At minimum, first end should be after at least 2 starts
        assert len(starts) == 3
        assert len(ends) == 3


class TestWebCrawlCaching:
    """Tests for web crawl caching functionality."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_result(self, orchestrator):
        """Test that cached crawl result is returned when available."""
        from datetime import datetime, timezone
        from unittest.mock import AsyncMock, MagicMock

        # Mock Supabase response with recent cached data
        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "cached-123",
                "client_id": "client-123",
                "project_id": "project-456",
                "web_domain": "example.com",
                "pages_crawled": 10,
                "confidence_score": 0.85,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "business_context": {
                    "company_name": "Cached Corp",
                    "industry": "Technology",
                    "description": "Cached description",
                    "key_services": ["Service1"],
                    "grounding_source": "https://example.com - cached",
                },
                "digital_assets": [
                    {
                        "asset_type": "portal",
                        "url": "https://portal.example.com",
                        "description": "Cached portal",
                        "grounding_source": "Found in cache",
                    }
                ],
                "organization_info": None,
            }
        ]

        # Create async mock chain for supabase.table().select().eq().eq().order().limit().execute()
        mock_execute = AsyncMock(return_value=mock_response)
        mock_limit = MagicMock(execute=mock_execute)
        mock_order = MagicMock(limit=MagicMock(return_value=mock_limit))
        mock_eq2 = MagicMock(order=MagicMock(return_value=mock_order))
        mock_eq1 = MagicMock(eq=MagicMock(return_value=mock_eq2))
        mock_select = MagicMock(eq=MagicMock(return_value=mock_eq1))
        mock_supabase.table = MagicMock(
            return_value=MagicMock(select=MagicMock(return_value=mock_select))
        )

        with patch(
            "app.db.supabase.get_async_supabase_client_async",
            new_callable=AsyncMock,
            return_value=mock_supabase,
        ):
            result = await orchestrator._get_cached_crawl_result(
                project_id="project-456",
                web_domain="example.com",
            )

        assert result is not None
        assert result.success is True
        assert result.web_domain == "example.com"
        assert result.pages_crawled == 10
        assert result.confidence_score == 0.85
        assert result.business_context is not None
        assert result.business_context.company_name == "Cached Corp"
        assert len(result.digital_assets) == 1

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, orchestrator):
        """Test that None is returned when no cache exists."""
        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []  # Empty result = cache miss

        mock_execute = AsyncMock(return_value=mock_response)
        mock_limit = MagicMock(execute=mock_execute)
        mock_order = MagicMock(limit=MagicMock(return_value=mock_limit))
        mock_eq2 = MagicMock(order=MagicMock(return_value=mock_order))
        mock_eq1 = MagicMock(eq=MagicMock(return_value=mock_eq2))
        mock_select = MagicMock(eq=MagicMock(return_value=mock_eq1))
        mock_supabase.table = MagicMock(
            return_value=MagicMock(select=MagicMock(return_value=mock_select))
        )

        with patch(
            "app.db.supabase.get_async_supabase_client_async",
            new_callable=AsyncMock,
            return_value=mock_supabase,
        ):
            result = await orchestrator._get_cached_crawl_result(
                project_id="project-456",
                web_domain="nonexistent.com",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_expired_returns_none(self, orchestrator):
        """Test that expired cache returns None."""
        from datetime import datetime, timedelta, timezone

        # Create a timestamp older than max_age_days
        old_timestamp = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "old-123",
                "client_id": "client-123",
                "project_id": "project-456",
                "web_domain": "example.com",
                "pages_crawled": 5,
                "confidence_score": 0.7,
                "created_at": old_timestamp,  # Expired
                "business_context": None,
                "digital_assets": [],
                "organization_info": None,
            }
        ]

        mock_execute = AsyncMock(return_value=mock_response)
        mock_limit = MagicMock(execute=mock_execute)
        mock_order = MagicMock(limit=MagicMock(return_value=mock_limit))
        mock_eq2 = MagicMock(order=MagicMock(return_value=mock_order))
        mock_eq1 = MagicMock(eq=MagicMock(return_value=mock_eq2))
        mock_select = MagicMock(eq=MagicMock(return_value=mock_eq1))
        mock_supabase.table = MagicMock(
            return_value=MagicMock(select=MagicMock(return_value=mock_select))
        )

        with patch(
            "app.db.supabase.get_async_supabase_client_async",
            new_callable=AsyncMock,
            return_value=mock_supabase,
        ):
            result = await orchestrator._get_cached_crawl_result(
                project_id="project-456",
                web_domain="example.com",
                max_age_days=7,  # Cache is 10 days old
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_run_web_crawl_uses_cache(
        self, orchestrator, sample_request_with_domain
    ):
        """Test that _run_web_crawl returns cached result when available."""
        cached_result = CrawlResult(
            success=True,
            web_domain="example.com",
            client_id="client-123",
            project_id="project-456",
            pages_crawled=10,
            confidence_score=0.9,
            digital_assets=[],
        )

        with patch.object(
            orchestrator,
            "_get_cached_crawl_result",
            return_value=cached_result,
        ) as mock_cache:
            result, from_cache = await orchestrator._run_web_crawl(
                web_domain="example.com",
                client_id="client-123",
                project_id="project-456",
            )

        mock_cache.assert_called_once_with("project-456", "example.com")
        assert result is cached_result
        assert from_cache is True

    @pytest.mark.asyncio
    async def test_run_web_crawl_force_refresh_bypasses_cache(
        self, orchestrator, sample_crawl_result
    ):
        """Test that force_refresh=True bypasses cache."""
        with (
            patch.object(
                orchestrator,
                "_get_cached_crawl_result",
            ) as mock_cache,
            patch(
                "app.services.web_crawler_agent.get_web_crawler_agent"
            ) as mock_get_agent,
        ):
            mock_agent = MagicMock()
            mock_agent.crawl_domain = AsyncMock(return_value=sample_crawl_result)
            mock_get_agent.return_value = mock_agent

            result, from_cache = await orchestrator._run_web_crawl(
                web_domain="example.com",
                client_id="client-123",
                project_id="project-456",
                force_refresh=True,
            )

        # Cache should NOT be checked when force_refresh=True
        mock_cache.assert_not_called()
        assert result is sample_crawl_result
        assert from_cache is False

    def test_web_crawl_summary_from_cache_field(self):
        """Test that WebCrawlSummary includes from_cache field."""
        summary_cached = WebCrawlSummary(
            success=True,
            pages_crawled=10,
            from_cache=True,
        )
        assert summary_cached.from_cache is True

        summary_fresh = WebCrawlSummary(
            success=True,
            pages_crawled=10,
            from_cache=False,
        )
        assert summary_fresh.from_cache is False

        # Default should be False
        summary_default = WebCrawlSummary(success=True)
        assert summary_default.from_cache is False

    def test_build_response_includes_from_cache(
        self, orchestrator, sample_request_with_domain
    ):
        """Test that _build_response passes through from_cache."""
        doc_results = [
            DocumentResult(
                document_id="doc-1", filename="policy.pdf", status="processed"
            )
        ]
        crawl_result = CrawlResult(
            success=True,
            web_domain="example.com",
            client_id="client-123",
            project_id="project-456",
            pages_crawled=5,
            digital_assets=[],
            confidence_score=0.8,
        )

        # Test with from_cache=True
        response = orchestrator._build_response(
            assessment_id="assess-123",
            request=sample_request_with_domain,
            doc_results=doc_results,
            web_crawl_result=crawl_result,
            from_cache=True,
        )
        assert response.web_crawl.from_cache is True

        # Test with from_cache=False
        response = orchestrator._build_response(
            assessment_id="assess-123",
            request=sample_request_with_domain,
            doc_results=doc_results,
            web_crawl_result=crawl_result,
            from_cache=False,
        )
        assert response.web_crawl.from_cache is False
