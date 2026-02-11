"""Knowledge graph models for Neo4j entities and relationships."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ComplianceLevel(str, Enum):
    """Compliance assessment levels for gap analysis."""

    COMPLIANT = "compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NON_COMPLIANT = "non_compliant"
    NOT_ASSESSED = "not_assessed"


class FrameworkType(str, Enum):
    """Supported compliance frameworks."""

    ISO_27001 = "iso_27001"
    BNM_RMIT = "bnm_rmit"


class DigitalAssetType(str, Enum):
    """Types of digital assets discovered from web crawl."""

    SUBDOMAIN = "subdomain"
    PORTAL = "portal"
    API = "api"
    APPLICATION = "application"
    WEBSITE = "website"


class PolicyType(str, Enum):
    """Types of policy documents."""

    SECURITY_POLICY = "security_policy"
    ACCEPTABLE_USE = "acceptable_use"
    DATA_PROTECTION = "data_protection"
    INCIDENT_RESPONSE = "incident_response"
    ACCESS_CONTROL = "access_control"
    BUSINESS_CONTINUITY = "business_continuity"
    RISK_MANAGEMENT = "risk_management"
    VENDOR_MANAGEMENT = "vendor_management"
    OTHER = "other"


# --- Node Models ---


class IndustryType(str, Enum):
    """Industry classifications for organizations."""

    BANKING = "Banking & Financial Services"
    INSURANCE = "Insurance"
    CAPITAL_MARKETS = "Capital Markets"
    HEALTHCARE = "Healthcare"
    GOVERNMENT = "Government & Public Sector"
    MANUFACTURING = "Manufacturing"
    TECHNOLOGY = "Technology & Software"
    TELECOMMUNICATIONS = "Telecommunications"
    RETAIL = "Retail & E-commerce"
    ENERGY = "Energy & Utilities"
    EDUCATION = "Education"
    OTHER = "Other"


class OrganizationNode(BaseModel):
    """
    Central organization node with ALL assessment context fields.

    This is the primary entity in the knowledge graph, storing all context
    needed for contextual question generation.
    """

    id: Optional[str] = Field(None, description="Neo4j node ID")
    client_id: str = Field(..., description="Client UUID - primary entity identifier")
    project_id: str = Field(..., description="Associated project UUID")

    # Core identity
    name: str = Field(..., description="Organization name")
    web_domain: Optional[str] = Field(None, description="Primary web domain")

    # Assessment context (from submission form)
    nature_of_business: Optional[str] = Field(
        None, description="Description of organization's business operations"
    )
    industry_type: Optional[str] = Field(
        None, description="Industry classification (IndustryType enum value)"
    )
    department: Optional[str] = Field(
        None, description="Department scope for assessment"
    )
    scope_statement_isms: Optional[str] = Field(
        None, description="ISMS scope statement defining assessment boundaries"
    )

    # Web crawler enrichment
    description: Optional[str] = Field(
        None, description="Business description from web crawl"
    )
    headquarters_location: Optional[str] = Field(None, description="HQ location")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


# Backward compatibility alias
CompanyNode = OrganizationNode


# --- Context Nodes (Separate from Organization for graph richness) ---


class BusinessContextNode(BaseModel):
    """
    Business context node storing nature of business description.

    Linked to Organization via HAS_BUSINESS_CONTEXT relationship.
    Allows for richer queries and context aggregation.
    """

    id: Optional[str] = Field(None, description="Neo4j node ID")
    project_id: str = Field(..., description="Associated project UUID")
    nature_of_business: str = Field(
        ..., description="Description of organization's business operations"
    )
    summary: Optional[str] = Field(
        None, description="AI-generated business context summary"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class IndustryNode(BaseModel):
    """
    Industry classification node - SHARED across organizations.

    Uses MERGE semantics to reuse existing industry nodes.
    Organizations link via IN_INDUSTRY relationship.
    Enables cross-org queries like "Find all Banking organizations".
    """

    id: Optional[str] = Field(None, description="Neo4j node ID")
    type: str = Field(..., description="Industry type (IndustryType enum value)")
    sector: Optional[str] = Field(
        None, description="Broader sector classification (e.g., 'Financial Services')"
    )
    description: Optional[str] = Field(
        None, description="Industry description for context"
    )


class DepartmentNode(BaseModel):
    """
    Department node for assessment scope.

    Linked to Organization via HAS_DEPARTMENT relationship.
    Multiple organizations can have departments with the same name
    but different project_ids.
    """

    id: Optional[str] = Field(None, description="Neo4j node ID")
    project_id: str = Field(..., description="Associated project UUID")
    name: str = Field(..., description="Department name")
    description: Optional[str] = Field(None, description="Department description")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ISMSScopeNode(BaseModel):
    """
    ISMS Scope statement node defining assessment boundaries.

    Linked to Organization via HAS_SCOPE relationship.
    Contains the formal scope statement and parsed boundaries.
    """

    id: Optional[str] = Field(None, description="Neo4j node ID")
    project_id: str = Field(..., description="Associated project UUID")
    statement: str = Field(..., description="Full ISMS scope statement")
    boundaries: list[str] = Field(
        default_factory=list,
        description="Parsed scope boundaries (e.g., systems, locations, processes)",
    )
    exclusions: list[str] = Field(
        default_factory=list,
        description="Explicitly excluded items from scope",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DigitalAssetNode(BaseModel):
    """Digital asset node discovered from web crawl."""

    id: Optional[str] = Field(None, description="Neo4j node ID")
    project_id: str = Field(..., description="Associated project UUID")
    organization_id: str = Field(..., description="Parent organization node ID")
    url: str = Field(..., description="Asset URL")
    asset_type: DigitalAssetType = Field(..., description="Type of digital asset")
    title: Optional[str] = Field(None, description="Page/app title")
    description: Optional[str] = Field(None, description="Asset description")
    technology_hints: list[str] = Field(
        default_factory=list, description="Detected technologies"
    )
    purpose: Optional[str] = Field(None, description="Asset purpose/function")
    discovered_at: datetime = Field(default_factory=datetime.utcnow)

    # Backward compatibility
    @property
    def company_id(self) -> str:
        return self.organization_id


class PolicyNode(BaseModel):
    """Policy document node."""

    id: Optional[str] = Field(None, description="Neo4j node ID")
    project_id: str = Field(..., description="Associated project UUID")
    document_id: str = Field(..., description="Supabase document UUID")
    title: str = Field(..., description="Policy title")
    policy_type: PolicyType = Field(..., description="Policy classification")
    version: Optional[str] = Field(None, description="Policy version")
    effective_date: Optional[datetime] = Field(None, description="Effective date")
    chunk_count: int = Field(0, description="Number of text chunks indexed")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentNode(BaseModel):
    """Generic document node (non-policy documents)."""

    id: Optional[str] = Field(None, description="Neo4j node ID")
    project_id: str = Field(..., description="Associated project UUID")
    document_id: str = Field(..., description="Supabase document UUID")
    filename: str = Field(..., description="Original filename")
    doc_type: str = Field(..., description="Document type/category")
    chunk_count: int = Field(0, description="Number of text chunks indexed")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ControlNode(BaseModel):
    """Compliance control node (ISO 27001 or BNM RMIT)."""

    id: Optional[str] = Field(None, description="Neo4j node ID")
    framework: FrameworkType = Field(..., description="Framework type")
    identifier: str = Field(..., description="Control identifier (e.g., A.5.1, 8.1)")
    title: str = Field(..., description="Control title")
    description: Optional[str] = Field(None, description="Control description")
    category: Optional[str] = Field(None, description="Control category/domain")


# --- Relationship Models ---


class PolicyControlMapping(BaseModel):
    """Relationship between a policy and a control."""

    policy_id: str = Field(..., description="Policy node ID")
    control_id: str = Field(..., description="Control node ID")
    compliance_level: ComplianceLevel = Field(..., description="Compliance assessment")
    evidence: Optional[str] = Field(None, description="Evidence text from policy")
    gap_description: Optional[str] = Field(None, description="Description of any gap")
    assessed_at: datetime = Field(default_factory=datetime.utcnow)


# --- Result Models ---


class ComplianceGapResult(BaseModel):
    """Gap analysis result for a single control."""

    control: ControlNode = Field(..., description="The control being assessed")
    compliance_level: ComplianceLevel = Field(
        ..., description="Current compliance level"
    )
    covering_policies: list[str] = Field(
        default_factory=list, description="Policy IDs that address this control"
    )
    gap_description: Optional[str] = Field(None, description="Description of the gap")
    recommendations: list[str] = Field(
        default_factory=list, description="Remediation recommendations"
    )


class GraphNode(BaseModel):
    """Generic graph node for visualization."""

    id: str = Field(..., description="Node ID")
    label: str = Field(..., description="Node label/type")
    properties: dict = Field(default_factory=dict, description="Node properties")


class GraphEdge(BaseModel):
    """Graph edge for visualization."""

    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    relationship: str = Field(..., description="Relationship type")
    properties: dict = Field(default_factory=dict, description="Edge properties")


class GraphQueryResult(BaseModel):
    """Result of a graph traversal query."""

    nodes: list[GraphNode] = Field(default_factory=list, description="Graph nodes")
    edges: list[GraphEdge] = Field(default_factory=list, description="Graph edges")
    node_count: int = Field(0, description="Total node count")
    edge_count: int = Field(0, description="Total edge count")


class GraphStats(BaseModel):
    """Statistics about the knowledge graph for a project."""

    project_id: str = Field(..., description="Project UUID")
    company_count: int = Field(0, description="Number of company nodes")
    policy_count: int = Field(0, description="Number of policy nodes")
    document_count: int = Field(0, description="Number of document nodes")
    digital_asset_count: int = Field(0, description="Number of digital assets")
    control_count: int = Field(0, description="Number of control mappings")
    # Context node counts
    business_context_count: int = Field(
        0, description="Number of business context nodes"
    )
    industry_count: int = Field(0, description="Number of unique industry nodes")
    department_count: int = Field(0, description="Number of department nodes")
    isms_scope_count: int = Field(0, description="Number of ISMS scope nodes")
    total_nodes: int = Field(0, description="Total nodes in graph")
    total_relationships: int = Field(0, description="Total relationships")
