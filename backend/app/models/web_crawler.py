"""Web crawler data models for CRAWL4AI agent."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DigitalAssetType(str, Enum):
    """Types of digital assets discovered during crawl."""

    SUBDOMAIN = "subdomain"
    PORTAL = "portal"
    API = "api"
    APPLICATION = "application"
    WEBSITE = "website"


# =============================================================================
# Grounded Extraction Models (with source citations)
# =============================================================================


class SocialMediaLink(BaseModel):
    """Social media link with platform identifier."""

    platform: str = Field(..., description="Platform name (e.g., LinkedIn, Twitter)")
    url: str = Field(..., description="URL to the social media profile")


class BusinessContext(BaseModel):
    """
    Extracted business context with grounding source.

    All fields must be explicitly found in source material.
    """

    company_name: str = Field(..., description="Official company name")
    industry: str = Field(..., description="Primary industry classification")
    description: str = Field(..., description="Company description from website")
    mission_statement: Optional[str] = Field(
        None, description="Company mission statement if found"
    )
    key_services: list[str] = Field(
        default_factory=list, description="List of key services/products"
    )
    target_audience: Optional[str] = Field(
        None, description="Target audience/market if stated"
    )
    grounding_source: str = Field(
        ..., description="Source URL + quoted text snippet proving extraction"
    )


class DigitalAsset(BaseModel):
    """
    Discovered digital asset with grounding source.

    Represents subdomains, portals, APIs, and other web resources.
    """

    asset_type: DigitalAssetType = Field(..., description="Type of digital asset")
    url: str = Field(..., description="Full URL of the asset")
    description: str = Field(..., description="Brief description of the asset")
    purpose: Optional[str] = Field(None, description="Purpose/function if identifiable")
    technology_hints: list[str] = Field(
        default_factory=list, description="Technology indicators found"
    )
    grounding_source: str = Field(
        ..., description="Source URL + evidence for this asset"
    )


class OrganizationInfo(BaseModel):
    """
    Organization contact and certification info with grounding.

    All fields extracted only when explicitly found.
    """

    headquarters_location: Optional[str] = Field(
        None, description="HQ location if stated"
    )
    contact_email: Optional[str] = Field(None, description="Contact email if public")
    contact_phone: Optional[str] = Field(None, description="Contact phone if public")
    social_media_links: list[SocialMediaLink] = Field(
        default_factory=list, description="Social media profiles found"
    )
    certifications: list[str] = Field(
        default_factory=list, description="Certifications/compliance badges"
    )
    partnerships: list[str] = Field(
        default_factory=list, description="Named partnerships"
    )
    grounding_source: str = Field(
        ..., description="Source URL(s) for organization info"
    )


# =============================================================================
# Crawl Request/Response Models
# =============================================================================


class CrawlRequest(BaseModel):
    """Request to start a web crawl."""

    web_domain: str = Field(..., description="Domain to crawl (e.g., example.com)")
    client_id: str = Field(..., description="Client UUID")
    project_id: str = Field(..., description="Project UUID")
    max_pages: int = Field(
        default=20, ge=1, le=50, description="Maximum pages to crawl (1-50)"
    )
    force_refresh: bool = Field(
        default=False, description="Force re-crawl even if cached data exists"
    )


class PageData(BaseModel):
    """Data extracted from a single crawled page."""

    url: str = Field(..., description="Page URL")
    title: Optional[str] = Field(None, description="Page title")
    content: str = Field(..., description="Extracted text content")
    word_count: int = Field(default=0, description="Word count of content")
    links: list[str] = Field(default_factory=list, description="Links found on page")
    crawl_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When page was crawled"
    )
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class AttackSurfaceSummary(BaseModel):
    """Summary of discovered attack surface."""

    total_assets: int = Field(default=0, description="Total assets discovered")
    asset_types: dict[str, int] = Field(
        default_factory=dict, description="Count by asset type"
    )
    technology_stack: list[str] = Field(
        default_factory=list, description="Detected technologies"
    )


class GraphCompany(BaseModel):
    """Company node for Neo4j graph."""

    id: Optional[str] = Field(None, description="Neo4j node ID")
    name: str = Field(..., description="Company name")
    domain: str = Field(..., description="Web domain")
    industry: Optional[str] = Field(None, description="Industry classification")
    description: Optional[str] = Field(None, description="Company description")
    project_id: Optional[str] = Field(None, description="Associated project")


class GraphAsset(BaseModel):
    """Digital asset node for Neo4j graph."""

    url: str = Field(..., description="Asset URL")
    asset_type: str = Field(..., description="Type of asset")
    description: Optional[str] = Field(None, description="Asset description")
    purpose: Optional[str] = Field(None, description="Asset purpose")
    technology_hints: list[str] = Field(
        default_factory=list, description="Technology hints"
    )


class CrawlResult(BaseModel):
    """
    Complete crawl result with all extracted data.

    Returned from POST /web-crawler/crawl endpoint.
    """

    success: bool = Field(..., description="Whether crawl completed successfully")
    web_domain: str = Field(..., description="Domain that was crawled")
    client_id: str = Field(..., description="Client UUID")
    project_id: str = Field(..., description="Project UUID")
    pages_crawled: int = Field(default=0, description="Number of pages crawled")
    total_words_analyzed: int = Field(
        default=0, description="Total words analyzed across all pages"
    )

    # Extracted data (nullable if extraction failed)
    business_context: Optional[BusinessContext] = Field(
        None, description="Extracted business context"
    )
    digital_assets: list[DigitalAsset] = Field(
        default_factory=list, description="Discovered digital assets"
    )
    organization_info: Optional[OrganizationInfo] = Field(
        None, description="Extracted organization info"
    )

    # Quality metrics
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence score (0.0-1.0)",
    )
    processing_time_ms: int = Field(
        default=0, description="Total processing time in milliseconds"
    )
    errors: list[str] = Field(
        default_factory=list, description="Any errors encountered"
    )

    # Security analysis (Phase 6)
    security_context: Optional["SecurityContext"] = Field(
        None, description="Security analysis results (headers, SSL, indicators)"
    )

    # Neo4j graph data (included in response)
    attack_surface: Optional[AttackSurfaceSummary] = Field(
        None, description="Attack surface summary"
    )
    graph_company: Optional[GraphCompany] = Field(
        None, description="Company node from graph"
    )
    graph_assets: list[GraphAsset] = Field(
        default_factory=list, description="Asset nodes from graph"
    )


class CrawlResultSummary(BaseModel):
    """Summary of a crawl result for listing."""

    id: str = Field(..., description="Result UUID")
    web_domain: str = Field(..., description="Domain crawled")
    pages_crawled: int = Field(..., description="Pages crawled")
    confidence_score: float = Field(..., description="Confidence score")
    created_at: datetime = Field(..., description="When crawl was performed")


class CrawlResultsListResponse(BaseModel):
    """Response for listing crawl results."""

    project_id: str = Field(..., description="Project UUID")
    results: list[CrawlResultSummary] = Field(..., description="List of results")
    total: int = Field(..., description="Total count")


class CrawlResultDetail(CrawlResultSummary):
    """Full crawl result from database."""

    client_id: str = Field(..., description="Client UUID")
    user_id: str = Field(..., description="User who initiated crawl")
    business_context: Optional[BusinessContext] = Field(None)
    digital_assets: list[DigitalAsset] = Field(default_factory=list)
    organization_info: Optional[OrganizationInfo] = Field(None)
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Neo4j graph data (when included)
    attack_surface: Optional[AttackSurfaceSummary] = Field(None)
    graph_company: Optional[GraphCompany] = Field(None)
    graph_assets: list[GraphAsset] = Field(default_factory=list)


# =============================================================================
# Confidence Scoring
# =============================================================================


class ConfidenceBreakdown(BaseModel):
    """Breakdown of confidence score calculation."""

    source_count_score: float = Field(
        ..., ge=0.0, le=1.0, description="Score based on number of sources"
    )
    text_clarity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Score based on text quality"
    )
    cross_validation_score: float = Field(
        ..., ge=0.0, le=1.0, description="Score based on cross-page consistency"
    )
    grounding_quality_score: float = Field(
        ..., ge=0.0, le=1.0, description="Score based on citation quality"
    )
    overall: float = Field(..., ge=0.0, le=1.0, description="Weighted overall score")


# =============================================================================
# Site Intelligence Models
# =============================================================================


class RobotsData(BaseModel):
    """Parsed robots.txt data."""

    allowed_paths: list[str] = Field(default_factory=list, description="Allowed crawl paths")
    disallowed_paths: list[str] = Field(
        default_factory=list, description="Disallowed crawl paths"
    )
    sitemaps: list[str] = Field(default_factory=list, description="Sitemap URLs found")
    crawl_delay: Optional[float] = Field(None, description="Crawl delay in seconds")


# =============================================================================
# Security Analysis Models
# =============================================================================


class SecurityHeadersResult(BaseModel):
    """Results from HTTP security header analysis."""

    has_csp: bool = Field(False, description="Content-Security-Policy present")
    has_hsts: bool = Field(False, description="Strict-Transport-Security present")
    has_x_frame_options: bool = Field(False, description="X-Frame-Options present")
    has_x_content_type: bool = Field(False, description="X-Content-Type-Options present")
    has_referrer_policy: bool = Field(False, description="Referrer-Policy present")
    headers_present: list[str] = Field(
        default_factory=list, description="Security headers found"
    )
    headers_missing: list[str] = Field(
        default_factory=list, description="Recommended headers missing"
    )
    score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Header security score"
    )


class SSLResult(BaseModel):
    """Results from SSL/TLS certificate analysis."""

    is_valid: bool = Field(False, description="Whether the certificate is valid")
    issuer: Optional[str] = Field(None, description="Certificate issuer")
    expires: Optional[str] = Field(None, description="Certificate expiry date")
    protocol_version: Optional[str] = Field(None, description="TLS protocol version")
    days_until_expiry: Optional[int] = Field(None, description="Days until cert expires")


class SecurityContext(BaseModel):
    """Combined security analysis for a domain."""

    headers: Optional[SecurityHeadersResult] = Field(
        None, description="HTTP security headers analysis"
    )
    ssl: Optional[SSLResult] = Field(None, description="SSL/TLS certificate analysis")
    security_indicators: list[str] = Field(
        default_factory=list,
        description="LLM-extracted security-related mentions from content",
    )
    robots_data: Optional[RobotsData] = Field(
        None, description="Parsed robots.txt data"
    )


# Resolve forward reference for CrawlResult.security_context
CrawlResult.model_rebuild()
