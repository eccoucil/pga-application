"""Tests for app.services.web_crawler.confidence."""

from datetime import datetime

from app.models.web_crawler import (
    BusinessContext,
    DigitalAsset,
    OrganizationInfo,
    PageData,
)
from app.services.web_crawler.confidence import calculate_confidence


def _make_page(word_count: int = 200, url: str = "https://example.com") -> PageData:
    return PageData(
        url=url,
        title="Test",
        content="word " * word_count,
        word_count=word_count,
        links=[],
        crawl_timestamp=datetime.utcnow(),
    )


def _make_business_context(grounding: str = "source text") -> BusinessContext:
    return BusinessContext(
        company_name="Test",
        industry="Tech",
        description="A test company",
        key_services=["SaaS"],
        grounding_source=grounding,
    )


def _make_asset(grounding: str = "source") -> DigitalAsset:
    return DigitalAsset(
        asset_type="website",
        url="https://example.com",
        description="Main site",
        grounding_source=grounding,
    )


def _make_org_info(grounding: str = "org source") -> OrganizationInfo:
    return OrganizationInfo(
        grounding_source=grounding,
    )


class TestCalculateConfidence:
    def test_no_extractions(self):
        """No business context, assets, or org info → low score."""
        pages = [_make_page()]
        result = calculate_confidence(pages, None, [], None)
        assert result.cross_validation_score == 0.0
        assert 0.0 <= result.overall <= 1.0

    def test_all_extractions_present(self):
        """All three extraction types present → high cross-validation."""
        pages = [_make_page() for _ in range(10)]
        bc = _make_business_context()
        assets = [_make_asset()]
        org = _make_org_info()

        result = calculate_confidence(pages, bc, assets, org)
        assert result.cross_validation_score == 1.0
        assert result.overall > 0.5

    def test_source_count_caps_at_max(self):
        """More than MAX_SOURCE_COUNT_PAGES still gives 1.0."""
        pages = [_make_page() for _ in range(20)]
        result = calculate_confidence(pages, None, [], None)
        assert result.source_count_score == 1.0

    def test_text_clarity_scales_with_word_count(self):
        """Higher average word count → higher text clarity score."""
        low_pages = [_make_page(word_count=50)]
        high_pages = [_make_page(word_count=500)]

        low_result = calculate_confidence(low_pages, None, [], None)
        high_result = calculate_confidence(high_pages, None, [], None)
        assert high_result.text_clarity_score > low_result.text_clarity_score

    def test_grounding_quality(self):
        """Extractions with grounding sources score higher."""
        pages = [_make_page()]
        bc_grounded = _make_business_context("quoted evidence")
        bc_ungrounded = _make_business_context("")

        grounded = calculate_confidence(pages, bc_grounded, [], None)
        ungrounded = calculate_confidence(pages, bc_ungrounded, [], None)
        assert grounded.grounding_quality_score >= ungrounded.grounding_quality_score

    def test_overall_in_range(self):
        """Overall score always between 0 and 1."""
        pages = [_make_page() for _ in range(5)]
        result = calculate_confidence(
            pages,
            _make_business_context(),
            [_make_asset(), _make_asset()],
            _make_org_info(),
        )
        assert 0.0 <= result.overall <= 1.0
