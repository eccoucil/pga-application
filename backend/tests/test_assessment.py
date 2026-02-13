"""Tests for assessment endpoints."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.dependencies import get_current_user
from app.models.assessment import DocumentResult
from app.services.assessment_orchestrator import reset_orchestrator


# Override auth dependency for testing
async def mock_get_current_user():
    """Mock user for testing - bypasses JWT validation."""
    return {
        "user_id": "test-user-id",
        "email": "test@example.com",
        "role": "authenticated",
    }


# Apply the override
app.dependency_overrides[get_current_user] = mock_get_current_user


@pytest.fixture
def client():
    """Create test client with auth override."""
    reset_orchestrator()
    return TestClient(app)


@pytest.fixture
def sample_document(tmp_path):
    """Create a sample document for testing."""
    doc = tmp_path / "policy.txt"
    doc.write_text("This is a sample policy document for testing compliance.")
    return doc


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check(self, client):
        """Health endpoint returns status (may be degraded without external services)."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        # Status can be "healthy" or "degraded" depending on Supabase availability
        assert data["status"] in ["healthy", "degraded"]


class TestAssessmentSubmit:
    """Tests for POST /assessment/submit endpoint."""

    @patch(
        "app.services.assessment_orchestrator.AssessmentOrchestrator._process_single_document",
        new_callable=AsyncMock,
    )
    def test_submit_assessment_success(
        self, mock_process_doc, client, sample_document
    ):
        """Successfully submit an assessment with a document."""
        mock_process_doc.return_value = DocumentResult(
            document_id=str(uuid.uuid4()),
            filename="policy.txt",
            status="pending",
        )

        with open(sample_document, "rb") as f:
            response = client.post(
                "/assessment/submit",
                data={
                    "client_id": "client-123",
                    "project_id": "project-456",
                    "organization_name": "Test Organization",
                    "nature_of_business": "Financial services and banking operations",
                    "industry_type": "Banking & Financial Services",
                    "department": "IT Security",
                    "scope_statement_isms": "ISMS covering all IT systems and data processing facilities",
                },
                files={"documents": ("policy.txt", f, "text/plain")},
            )

        assert response.status_code == 200
        data = response.json()
        assert "assessment_id" in data
        assert data["project_id"] == "project-456"
        assert data["documents_received"] == 1
        assert data["status"] == "received"
        assert len(data["documents"]) == 1
        assert data["documents"][0]["filename"] == "policy.txt"
        assert data["documents"][0]["status"] == "pending"

    def test_submit_assessment_multiple_documents(self, client, tmp_path):
        """Submit assessment with multiple documents."""
        # Create multiple test files
        doc1 = tmp_path / "policy1.pdf"
        doc2 = tmp_path / "policy2.docx"
        doc1.write_bytes(b"%PDF-1.4 fake pdf content")
        doc2.write_bytes(b"PK fake docx content")

        with open(doc1, "rb") as f1, open(doc2, "rb") as f2:
            response = client.post(
                "/assessment/submit",
                data={
                    "client_id": "client-123",
                    "project_id": "project-789",
                    "organization_name": "Multi Doc Corp",
                    "nature_of_business": "Technology consulting services",
                    "industry_type": "Technology",
                    "department": "Compliance",
                    "scope_statement_isms": "ISMS covering all IT systems and data processing facilities",
                },
                files=[
                    ("documents", ("policy1.pdf", f1, "application/pdf")),
                    (
                        "documents",
                        (
                            "policy2.docx",
                            f2,
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        ),
                    ),
                ],
            )

        assert response.status_code == 200
        data = response.json()
        assert data["documents_received"] == 2
        assert len(data["documents"]) == 2

    def test_submit_assessment_missing_document(self, client):
        """Submit assessment without documents (allowed - documents are optional)."""
        response = client.post(
            "/assessment/submit",
            data={
                "client_id": "client-123",
                "project_id": "project-456",
                "organization_name": "Test Org",
                "nature_of_business": "Financial services operations",
                "industry_type": "Banking & Financial Services",
                "department": "IT",
                "scope_statement_isms": "ISMS covering all IT systems and data processing facilities",
            },
        )

        # Documents are optional, so this should succeed
        assert response.status_code == 200

    def test_submit_assessment_short_business_description(
        self, client, sample_document
    ):
        """Reject submission with too-short business description."""
        with open(sample_document, "rb") as f:
            response = client.post(
                "/assessment/submit",
                data={
                    "client_id": "client-123",
                    "project_id": "project-456",
                    "organization_name": "Test Org",
                    "nature_of_business": "Short",  # Less than 10 chars
                    "industry_type": "Technology",
                    "department": "IT",
                    "scope_statement_isms": "ISMS covering all IT systems and data processing facilities",
                },
                files={"documents": ("policy.txt", f, "text/plain")},
            )

        assert response.status_code == 422  # Validation error

    def test_submit_assessment_invalid_industry(self, client, sample_document):
        """Reject submission with invalid industry type."""
        with open(sample_document, "rb") as f:
            response = client.post(
                "/assessment/submit",
                data={
                    "client_id": "client-123",
                    "project_id": "project-456",
                    "organization_name": "Test Org",
                    "nature_of_business": "Valid business description here",
                    "industry_type": "InvalidIndustry",
                    "department": "IT",
                    "scope_statement_isms": "ISMS covering all IT systems and data processing facilities",
                },
                files={"documents": ("policy.txt", f, "text/plain")},
            )

        assert response.status_code == 422  # Validation error

    def test_submit_assessment_unsupported_file_type(self, client, tmp_path):
        """Reject submission with unsupported file type."""
        bad_file = tmp_path / "script.exe"
        bad_file.write_bytes(b"MZ fake exe")

        with open(bad_file, "rb") as f:
            response = client.post(
                "/assessment/submit",
                data={
                    "client_id": "client-123",
                    "project_id": "project-456",
                    "organization_name": "Test Org",
                    "nature_of_business": "Valid business description",
                    "industry_type": "Technology",
                    "department": "IT",
                    "scope_statement_isms": "ISMS covering all IT systems and data processing facilities",
                },
                files={"documents": ("script.exe", f, "application/octet-stream")},
            )

        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_submit_assessment_with_optional_domain(self, client, sample_document):
        """Submit assessment with optional web domain."""
        with open(sample_document, "rb") as f:
            response = client.post(
                "/assessment/submit",
                data={
                    "client_id": "client-123",
                    "project_id": "project-456",
                    "organization_name": "Domain Test Corp",
                    "nature_of_business": "E-commerce platform operations",
                    "industry_type": "Retail",
                    "department": "Security",
                    "scope_statement_isms": "ISMS covering all IT systems and data processing facilities",
                    "web_domain": "example.com",
                },
                files={"documents": ("policy.txt", f, "text/plain")},
            )

        assert response.status_code == 200
        data = response.json()
        # Status can vary based on web crawl result (received/partial/failed)
        assert data["status"] in ["received", "partial", "failed"]


class TestAssessmentStatus:
    """Tests for GET /assessment/status/{assessment_id} endpoint."""

    def test_get_assessment_status_success(self, client, sample_document):
        """Get status of a submitted assessment."""
        # First submit an assessment
        with open(sample_document, "rb") as f:
            submit_response = client.post(
                "/assessment/submit",
                data={
                    "client_id": "client-123",
                    "project_id": "project-456",
                    "organization_name": "Status Test Corp",
                    "nature_of_business": "Testing status endpoint functionality",
                    "industry_type": "Technology",
                    "department": "QA",
                    "scope_statement_isms": "ISMS covering all IT systems and data processing facilities",
                },
                files={"documents": ("policy.txt", f, "text/plain")},
            )

        assessment_id = submit_response.json()["assessment_id"]

        # Get status
        response = client.get(f"/assessment/status/{assessment_id}")
        assert response.status_code == 200
        data = response.json()
        # Status progresses from received -> processing
        assert data["status"] in ["received", "processing"]
        assert "request" in data
        assert "documents" in data

    def test_get_assessment_status_not_found(self, client):
        """Return 404 for non-existent assessment."""
        response = client.get("/assessment/status/non-existent-id")
        assert response.status_code == 404
        assert response.json()["detail"] == "Assessment not found"


class TestIndustryTypes:
    """Test all valid industry types are accepted."""

    @pytest.mark.parametrize(
        "industry",
        [
            "Banking & Financial Services",
            "Insurance",
            "Healthcare",
            "Technology",
            "Manufacturing",
            "Retail",
            "Government",
            "Other",
        ],
    )
    def test_valid_industry_types(self, client, sample_document, industry):
        """All defined industry types should be accepted."""
        with open(sample_document, "rb") as f:
            response = client.post(
                "/assessment/submit",
                data={
                    "client_id": "client-123",
                    "project_id": "project-456",
                    "organization_name": f"Test {industry} Corp",
                    "nature_of_business": f"Business operations in {industry} sector",
                    "industry_type": industry,
                    "department": "Compliance",
                    "scope_statement_isms": "ISMS covering all IT systems and data processing facilities",
                },
                files={"documents": ("policy.txt", f, "text/plain")},
            )

        assert response.status_code == 200
