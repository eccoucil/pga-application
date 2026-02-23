"""Assessment request and response models."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class IndustryType(str, Enum):
    """Supported industry types for assessments."""

    BANKING = "Banking & Financial Services"
    INSURANCE = "Insurance"
    HEALTHCARE = "Healthcare"
    TECHNOLOGY = "Technology"
    MANUFACTURING = "Manufacturing"
    RETAIL = "Retail"
    GOVERNMENT = "Government"
    OTHER = "Other"


class OrganizationInfo(BaseModel):
    """Organization information for assessment context."""

    organization_name: str = Field(..., description="Name of the organization")
    nature_of_business: str = Field(
        ...,
        min_length=10,
        description="Description of business activities (min 10 chars)",
    )
    industry_type: IndustryType = Field(..., description="Industry classification")
    web_domain: Optional[str] = Field(
        None, description="Organization's web domain for discovery"
    )
    department: str = Field(
        ...,
        description="Department(s) requesting assessment (comma-separated for multiple departments)",
    )
    scope_statement_isms: str = Field(
        ...,
        min_length=10,
        description="Scope statement for Information Security Management System (min 10 chars)",
    )


class AssessmentRequest(BaseModel):
    """Full assessment submission request."""

    client_id: str = Field(..., description="Client UUID from Supabase")
    project_id: str = Field(..., description="Project UUID from Supabase")
    organization_info: OrganizationInfo = Field(
        ..., description="Organization context for assessment"
    )


class DocumentResult(BaseModel):
    """Status of a single document in the assessment."""

    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    status: str = Field(
        default="pending",
        description="Processing status: pending, processing, processed, failed",
    )
    extracted_text_length: int = Field(
        default=0, description="Length of extracted text (0 if not processed)"
    )
    findings_count: int = Field(
        default=0, description="Number of compliance findings (0 if not analyzed)"
    )


class WebCrawlSummary(BaseModel):
    """Summary of web crawl results in assessment response."""

    success: bool = Field(..., description="Whether web crawl succeeded")
    pages_crawled: int = Field(default=0, description="Number of pages crawled")
    digital_assets_found: int = Field(
        default=0, description="Number of digital assets discovered"
    )
    business_context_extracted: bool = Field(
        default=False, description="Whether business context was extracted"
    )
    organization_info_extracted: bool = Field(
        default=False, description="Whether organization info was extracted"
    )
    confidence_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Overall confidence score"
    )
    errors: list[str] = Field(
        default_factory=list, description="Any errors encountered during crawl"
    )
    from_cache: bool = Field(
        default=False, description="Whether result was served from cache"
    )
    business_context: Optional[dict] = Field(
        None,
        description="Extracted business context (company info, services, industry)",
    )
    digital_assets: list[dict] = Field(
        default_factory=list,
        description="Discovered digital assets (subdomains, portals, APIs)",
    )
    organization_info: Optional[dict] = Field(
        None,
        description="Extracted organization info (contacts, certifications, partnerships)",
    )


class Neo4jNodeReference(BaseModel):
    """Reference to a Neo4j node with its ID and key data."""

    node_id: str = Field(..., description="Neo4j element ID")
    node_type: str = Field(..., description="Node label (Organization, Industry, etc.)")
    name: Optional[str] = Field(None, description="Node name/identifier")


# React Flow compatible graph models
class GraphNodePosition(BaseModel):
    """Position for React Flow node."""

    x: float = Field(default=0, description="X coordinate")
    y: float = Field(default=0, description="Y coordinate")


class GraphNodeData(BaseModel):
    """Data payload for React Flow node."""

    label: str = Field(..., description="Display label for the node")
    node_type: str = Field(..., description="Node type (Organization, Industry, etc.)")
    neo4j_id: Optional[str] = Field(None, description="Neo4j element ID")
    properties: dict = Field(
        default_factory=dict, description="Additional node properties"
    )


class GraphNode(BaseModel):
    """React Flow compatible node."""

    id: str = Field(..., description="Unique node identifier")
    type: str = Field(default="default", description="React Flow node type")
    position: GraphNodePosition = Field(
        default_factory=GraphNodePosition, description="Node position"
    )
    data: GraphNodeData = Field(..., description="Node data payload")


class GraphEdge(BaseModel):
    """React Flow compatible edge."""

    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: str = Field(default="default", description="React Flow edge type")
    label: Optional[str] = Field(None, description="Edge label (relationship type)")
    animated: bool = Field(default=False, description="Whether edge is animated")


class KnowledgeGraph(BaseModel):
    """React Flow compatible knowledge graph structure."""

    nodes: list[GraphNode] = Field(
        default_factory=list, description="Graph nodes for React Flow"
    )
    edges: list[GraphEdge] = Field(
        default_factory=list, description="Graph edges for React Flow"
    )


class OrganizationContextSummary(BaseModel):
    """Summary of organization context stored in Neo4j."""

    created: bool = Field(..., description="Whether Organization node was created")
    organization_id: Optional[str] = Field(
        None, description="Neo4j Organization node ID"
    )
    organization_name: str = Field(..., description="Organization name from Neo4j")
    industry_type: str = Field(..., description="Industry classification")
    industry_sector: Optional[str] = Field(
        None, description="Industry sector (e.g., Financial Services)"
    )
    department: str = Field(..., description="Department for assessment")
    scope_statement_preview: str = Field(
        ..., description="First 100 chars of ISMS scope statement"
    )
    web_domain: Optional[str] = Field(None, description="Web domain if provided")
    context_nodes: list[Neo4jNodeReference] = Field(
        default_factory=list,
        description="References to created context nodes with their Neo4j IDs",
    )
    context_nodes_created: list[str] = Field(
        default_factory=list,
        description="List of context node types created (backward compatibility)",
    )


class AssessmentSummary(BaseModel):
    """Human-readable summary for frontend display."""

    headline: str = Field(
        ...,
        description="One-line summary (e.g., 'Assessment received for Apex Financial Services')",
    )
    processing_time_ms: int = Field(
        ..., description="Total processing time in milliseconds"
    )
    highlights: list[str] = Field(
        default_factory=list,
        description="Key highlights (e.g., '3 documents queued', '5 digital assets discovered')",
    )
    next_step: str = Field(
        default="review_findings",
        description="Suggested next action: review_findings, upload_more_docs",
    )
    next_step_url: Optional[str] = Field(
        None, description="Relative URL for next step navigation"
    )


class AssessmentResponse(BaseModel):
    """Response acknowledging assessment submission."""

    assessment_id: str = Field(..., description="Unique assessment identifier")
    project_id: str = Field(..., description="Associated project ID")
    documents_received: int = Field(..., description="Number of documents uploaded")
    status: str = Field(
        default="received",
        description="Assessment status: received, processing, completed, failed, partial",
    )
    documents: list[DocumentResult] = Field(
        default_factory=list, description="Individual document statuses"
    )
    web_crawl: Optional[WebCrawlSummary] = Field(
        None, description="Web crawl results (when web_domain provided)"
    )
    organization_context: OrganizationContextSummary = Field(
        ..., description="Organization context stored in Neo4j"
    )
    knowledge_graph: KnowledgeGraph = Field(
        default_factory=KnowledgeGraph,
        description="React Flow compatible knowledge graph for visualization",
    )
    summary: AssessmentSummary = Field(
        ..., description="Human-readable summary for frontend display"
    )


class AssessmentRecord(BaseModel):
    """Lightweight assessment record for table display."""

    id: str
    version: int
    organization_name: str
    industry_type: str
    department: str
    status: str
    documents_count: int
    created_at: str
class AssessmentListResponse(BaseModel):
    """Response for GET /assessment/list."""

    assessments: list[AssessmentRecord]
    total: int


class AssessmentDetailResponse(BaseModel):
    """Full assessment detail for viewing/editing."""
    id: str
    version: int
    organization_name: str
    nature_of_business: str
    industry_type: str
    department: str
    scope_statement_isms: str
    web_domain: Optional[str] = None
    status: str
    documents_count: int
    response_snapshot: Optional[dict] = None
    created_at: str
