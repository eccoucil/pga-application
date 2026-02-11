"""Confidence scoring logic for crawl results.

Extracted from ``WebCrawlerAgent._calculate_confidence`` so it can be
unit-tested independently.
"""

from typing import Optional

from app.models.web_crawler import (
    BusinessContext,
    ConfidenceBreakdown,
    DigitalAsset,
    OrganizationInfo,
    PageData,
)
from app.services.web_crawler.constants import (
    CONFIDENCE_WEIGHT_CROSS_VALIDATION,
    CONFIDENCE_WEIGHT_GROUNDING,
    CONFIDENCE_WEIGHT_SOURCE_COUNT,
    CONFIDENCE_WEIGHT_TEXT_CLARITY,
    MAX_AVG_WORD_COUNT,
    MAX_SOURCE_COUNT_PAGES,
)


def calculate_confidence(
    pages: list[PageData],
    business_context: Optional[BusinessContext],
    assets: list[DigitalAsset],
    org_info: Optional[OrganizationInfo],
) -> ConfidenceBreakdown:
    """Calculate a multi-factor confidence score for a crawl result.

    Returns:
        ``ConfidenceBreakdown`` with per-factor scores and a weighted overall.
    """
    # Source count score (more pages = higher confidence)
    source_count_score = min(len(pages) / MAX_SOURCE_COUNT_PAGES, 1.0)

    # Text clarity score (average word count per page)
    avg_words = sum(p.word_count for p in pages) / max(len(pages), 1)
    text_clarity_score = min(avg_words / MAX_AVG_WORD_COUNT, 1.0)

    # Cross-validation score (presence of multiple data types)
    has_business = business_context is not None
    has_assets = len(assets) > 0
    has_org = org_info is not None
    cross_validation_score = (has_business + has_assets + has_org) / 3

    # Grounding quality score
    grounded_count = 0
    total_count = 0
    if business_context:
        total_count += 1
        if business_context.grounding_source:
            grounded_count += 1
    for asset in assets:
        total_count += 1
        if asset.grounding_source:
            grounded_count += 1
    if org_info:
        total_count += 1
        if org_info.grounding_source:
            grounded_count += 1
    grounding_quality_score = grounded_count / max(total_count, 1)

    # Weighted overall
    overall = (
        source_count_score * CONFIDENCE_WEIGHT_SOURCE_COUNT
        + text_clarity_score * CONFIDENCE_WEIGHT_TEXT_CLARITY
        + cross_validation_score * CONFIDENCE_WEIGHT_CROSS_VALIDATION
        + grounding_quality_score * CONFIDENCE_WEIGHT_GROUNDING
    )

    return ConfidenceBreakdown(
        source_count_score=source_count_score,
        text_clarity_score=text_clarity_score,
        cross_validation_score=cross_validation_score,
        grounding_quality_score=grounding_quality_score,
        overall=overall,
    )
