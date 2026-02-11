"""
Context Aggregator Service for Contextual Question Generation.

Builds a unified context profile from:
1. Neo4j Organization node (assessment form data)
2. Neo4j linked entities (digital assets, documents, services, certifications)
3. Qdrant document chunks (semantic search for section-relevant content)
4. Supabase web_crawl_results (business context, organization info)

The unified context profile is used by the QuestionGenerator to create
industry-specific, contextual compliance questions.
"""

import logging
from typing import Optional

from pydantic import BaseModel, Field

from app.services.neo4j_service import get_neo4j_service
from app.services.qdrant_service import get_qdrant_service
from app.config import get_settings

logger = logging.getLogger(__name__)


class DigitalAssetContext(BaseModel):
    """Digital asset context for question generation."""

    url: str
    asset_type: str
    title: Optional[str] = None
    purpose: Optional[str] = None
    technology_hints: list[str] = Field(default_factory=list)


class DocumentContext(BaseModel):
    """Document context showing what policies exist."""

    filename: str
    extraction_type: Optional[str] = None
    controls_referenced: list[str] = Field(default_factory=list)


class OrganizationContext(BaseModel):
    """Core organization context from assessment form and linked nodes."""

    name: str
    industry_type: Optional[str] = None
    industry_sector: Optional[str] = None  # Broader sector from Industry node
    nature_of_business: Optional[str] = None
    business_context_summary: Optional[str] = (
        None  # AI summary from BusinessContext node
    )
    department: Optional[str] = None
    department_description: Optional[str] = None  # From Department node
    scope_statement_isms: Optional[str] = None
    scope_boundaries: list[str] = Field(default_factory=list)  # From ISMSScope node
    scope_exclusions: list[str] = Field(default_factory=list)  # From ISMSScope node
    web_domain: Optional[str] = None
    uses_context_nodes: bool = False  # Flag indicating new architecture


class DiscoveredContext(BaseModel):
    """Context discovered from web crawl and documents."""

    services: list[str] = Field(default_factory=list)
    digital_assets: list[DigitalAssetContext] = Field(default_factory=list)
    technology_hints: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    partnerships: list[str] = Field(default_factory=list)


class ExistingPolicies(BaseModel):
    """Context about existing policies from document analysis."""

    controls_addressed: list[str] = Field(default_factory=list)
    policy_summaries: list[DocumentContext] = Field(default_factory=list)


class RiskProfile(BaseModel):
    """Risk profile based on industry, department, and asset exposure."""

    industry_risks: list[str] = Field(default_factory=list)
    department_risks: list[str] = Field(default_factory=list)
    department_focus: Optional[dict] = Field(
        default=None,
        description="Department-specific assets, controls, and evidence types",
    )
    asset_exposure: str = "medium"  # low, medium, high
    regulatory_pressure: str = "medium"  # low, medium, high


class UnifiedContextProfile(BaseModel):
    """
    Unified context profile for question generation.

    This is the primary data structure passed to the QuestionGenerator
    along with control definitions.
    """

    organization: OrganizationContext
    discovered_context: DiscoveredContext = Field(default_factory=DiscoveredContext)
    existing_policies: ExistingPolicies = Field(default_factory=ExistingPolicies)
    risk_profile: RiskProfile = Field(default_factory=RiskProfile)

    # Relevant document chunks for the current section (from Qdrant)
    relevant_chunks: list[str] = Field(default_factory=list)


# Industry-specific risk mappings
INDUSTRY_RISKS = {
    "Banking & Financial Services": [
        "Financial fraud",
        "Data breach",
        "Regulatory non-compliance (BNM, PCI DSS)",
        "Money laundering",
        "Insider trading",
    ],
    "Insurance": [
        "Claims fraud",
        "Data privacy violations",
        "Regulatory non-compliance (BNM)",
        "Actuarial data integrity",
    ],
    "Capital Markets": [
        "Market manipulation",
        "Trading system integrity",
        "Regulatory non-compliance (SC)",
        "Insider information leakage",
    ],
    "Healthcare": [
        "Patient data breach (PHI)",
        "PDPA violations",
        "Medical device security",
        "Clinical system availability",
    ],
    "Government & Public Sector": [
        "National security risks",
        "Citizen data privacy",
        "Critical infrastructure protection",
        "Service availability",
    ],
    "Manufacturing": [
        "OT/ICS security",
        "Supply chain attacks",
        "Intellectual property theft",
        "Production system availability",
    ],
    "Technology & Software": [
        "Source code theft",
        "DevSecOps vulnerabilities",
        "API security",
        "Cloud misconfiguration",
    ],
    "Telecommunications": [
        "Network infrastructure attacks",
        "Customer data privacy",
        "Service availability",
        "Lawful interception compliance",
    ],
    "Retail & E-commerce": [
        "Payment card data (PCI DSS)",
        "Customer data breach",
        "E-commerce fraud",
        "Supply chain security",
    ],
    "Energy & Utilities": [
        "SCADA/ICS security",
        "Critical infrastructure attacks",
        "Environmental system integrity",
        "Grid reliability",
    ],
    "Education": [
        "Student data privacy",
        "Research data protection",
        "Academic integrity systems",
        "Remote learning security",
    ],
}


# Department-specific risk mappings
DEPARTMENT_RISKS = {
    "Human Resources": [
        "Personnel data breach (PII, salary, performance records)",
        "Insider threat from disgruntled employees",
        "Onboarding/offboarding security gaps",
        "Unauthorized access to HR systems",
        "Background screening failures",
    ],
    "Information Technology": [
        "System vulnerabilities and misconfigurations",
        "Unauthorized access to production systems",
        "Source code exposure or theft",
        "API security weaknesses",
        "Cloud infrastructure mismanagement",
    ],
    "Finance": [
        "Financial fraud and embezzlement",
        "Audit trail manipulation",
        "Unauthorized transaction approvals",
        "Payment system vulnerabilities",
        "Financial reporting integrity",
    ],
    "Operations": [
        "Business continuity disruption",
        "Supply chain security incidents",
        "Process automation failures",
        "Vendor/third-party access risks",
        "Operational data integrity",
    ],
    "Legal & Compliance": [
        "Regulatory non-compliance penalties",
        "Contract data confidentiality breach",
        "Legal hold and e-discovery failures",
        "Privacy law violations (PDPA, GDPR)",
        "Intellectual property exposure",
    ],
    "Risk Management": [
        "Risk assessment data integrity",
        "Control monitoring failures",
        "Incident response inadequacies",
        "Risk reporting manipulation",
        "Third-party risk oversight gaps",
    ],
    "Internal Audit": [
        "Audit evidence tampering",
        "Audit system access controls",
        "Confidential findings disclosure",
        "Audit trail integrity",
        "Independence compromise",
    ],
    "Security": [
        "Physical security breaches",
        "Access control system failures",
        "Security monitoring gaps",
        "Incident detection delays",
        "Security tool misconfigurations",
    ],
    "Customer Service": [
        "Customer data exposure during support",
        "Social engineering via support channels",
        "Unauthorized account access",
        "Call recording confidentiality",
        "Customer identity verification failures",
    ],
    "Marketing": [
        "Customer analytics data misuse",
        "Marketing database breaches",
        "Social media account compromise",
        "Brand reputation incidents",
        "Third-party marketing tool risks",
    ],
    "Sales": [
        "CRM data confidentiality breach",
        "Prospect/customer data exposure",
        "Sales system access abuse",
        "Competitive intelligence leakage",
        "Contract negotiation data exposure",
    ],
    "Research & Development": [
        "Intellectual property theft",
        "Research data confidentiality breach",
        "Development environment compromise",
        "Prototype and trade secret exposure",
        "Collaboration tool security gaps",
    ],
}


# Department-specific focus areas for question generation
DEPARTMENT_FOCUS = {
    "Human Resources": {
        "primary_assets": [
            "employee personal records",
            "payroll and compensation data",
            "performance evaluations",
            "recruitment databases",
            "training records",
        ],
        "key_controls": [
            "access provisioning/deprovisioning",
            "background screening procedures",
            "security awareness training",
            "employment contract security clauses",
            "exit interview and offboarding",
        ],
        "evidence_types": [
            "access request and approval forms",
            "training completion records",
            "offboarding checklists",
            "background check reports",
            "security acknowledgment signatures",
        ],
    },
    "Information Technology": {
        "primary_assets": [
            "source code repositories",
            "production infrastructure",
            "APIs and integrations",
            "databases and data stores",
            "network infrastructure",
        ],
        "key_controls": [
            "change management procedures",
            "access control and authentication",
            "vulnerability management",
            "configuration management",
            "backup and recovery",
        ],
        "evidence_types": [
            "access logs and audit trails",
            "change request records",
            "vulnerability scan reports",
            "configuration baselines",
            "backup verification records",
        ],
    },
    "Finance": {
        "primary_assets": [
            "financial systems and ERP",
            "payment processing systems",
            "financial records and reports",
            "banking credentials",
            "audit documentation",
        ],
        "key_controls": [
            "segregation of duties",
            "transaction approval workflows",
            "financial system access controls",
            "audit trail maintenance",
            "reconciliation procedures",
        ],
        "evidence_types": [
            "approval matrices",
            "transaction logs",
            "reconciliation reports",
            "access review records",
            "audit findings and responses",
        ],
    },
    "Operations": {
        "primary_assets": [
            "operational systems",
            "process documentation",
            "vendor/supplier data",
            "logistics systems",
            "inventory databases",
        ],
        "key_controls": [
            "business continuity planning",
            "vendor management procedures",
            "process automation controls",
            "operational monitoring",
            "incident management",
        ],
        "evidence_types": [
            "BCP/DR test records",
            "vendor assessments",
            "process flow documentation",
            "operational metrics",
            "incident reports",
        ],
    },
    "Legal & Compliance": {
        "primary_assets": [
            "contracts and legal documents",
            "compliance records",
            "regulatory filings",
            "legal case files",
            "policy documentation",
        ],
        "key_controls": [
            "document classification",
            "legal hold procedures",
            "regulatory monitoring",
            "contract management",
            "privacy compliance",
        ],
        "evidence_types": [
            "compliance audit reports",
            "regulatory correspondence",
            "contract review records",
            "privacy impact assessments",
            "legal opinion documentation",
        ],
    },
    "Risk Management": {
        "primary_assets": [
            "risk registers",
            "risk assessment reports",
            "control testing results",
            "incident databases",
            "risk metrics dashboards",
        ],
        "key_controls": [
            "risk assessment methodology",
            "control effectiveness monitoring",
            "risk reporting procedures",
            "third-party risk assessments",
            "key risk indicator tracking",
        ],
        "evidence_types": [
            "risk assessment documentation",
            "control test results",
            "risk committee minutes",
            "KRI reports",
            "third-party assessments",
        ],
    },
    "Internal Audit": {
        "primary_assets": [
            "audit workpapers",
            "audit reports",
            "audit management system",
            "evidence repositories",
            "audit findings database",
        ],
        "key_controls": [
            "audit independence safeguards",
            "workpaper security",
            "audit evidence integrity",
            "audit report confidentiality",
            "follow-up tracking",
        ],
        "evidence_types": [
            "audit charter and plans",
            "workpaper review records",
            "audit committee reports",
            "independence declarations",
            "remediation tracking",
        ],
    },
    "Security": {
        "primary_assets": [
            "security monitoring systems",
            "access control systems",
            "CCTV and surveillance",
            "security incident data",
            "threat intelligence",
        ],
        "key_controls": [
            "security operations monitoring",
            "physical access controls",
            "incident response procedures",
            "threat detection and analysis",
            "security awareness programs",
        ],
        "evidence_types": [
            "security monitoring logs",
            "access control records",
            "incident response reports",
            "penetration test results",
            "security metrics",
        ],
    },
    "Customer Service": {
        "primary_assets": [
            "customer interaction records",
            "support ticket systems",
            "call recordings",
            "customer account data",
            "knowledge bases",
        ],
        "key_controls": [
            "customer identity verification",
            "data handling procedures",
            "call recording management",
            "support system access controls",
            "escalation procedures",
        ],
        "evidence_types": [
            "identity verification logs",
            "call handling records",
            "quality assurance reviews",
            "access audit trails",
            "customer complaint records",
        ],
    },
    "Marketing": {
        "primary_assets": [
            "marketing databases",
            "customer analytics platforms",
            "social media accounts",
            "campaign management systems",
            "brand assets",
        ],
        "key_controls": [
            "consent management",
            "data retention compliance",
            "social media security",
            "third-party tool vetting",
            "brand protection",
        ],
        "evidence_types": [
            "consent records",
            "data processing agreements",
            "social media access logs",
            "vendor security assessments",
            "campaign approval records",
        ],
    },
    "Sales": {
        "primary_assets": [
            "CRM systems",
            "sales pipeline data",
            "customer contact information",
            "pricing and proposal data",
            "contract negotiations",
        ],
        "key_controls": [
            "CRM access controls",
            "data sharing restrictions",
            "mobile device management",
            "sales data classification",
            "partner portal security",
        ],
        "evidence_types": [
            "CRM access reviews",
            "data export logs",
            "mobile device compliance",
            "classification records",
            "partner access audits",
        ],
    },
    "Research & Development": {
        "primary_assets": [
            "research data and results",
            "intellectual property",
            "development environments",
            "prototypes and designs",
            "collaboration platforms",
        ],
        "key_controls": [
            "IP protection measures",
            "secure development practices",
            "research data classification",
            "collaboration tool security",
            "third-party research agreements",
        ],
        "evidence_types": [
            "IP registration records",
            "code review records",
            "data classification logs",
            "NDA and collaboration agreements",
            "security testing results",
        ],
    },
}


class ContextAggregator:
    """
    Aggregates context from multiple sources for question generation.

    Usage:
        aggregator = ContextAggregator()
        context = await aggregator.build_context(
            client_id="...",
            project_id="...",
            section="A.5",  # Optional: for section-specific chunks
        )
    """

    def __init__(self):
        self._neo4j = get_neo4j_service()
        self._qdrant = get_qdrant_service()
        self._settings = get_settings()

    async def build_context(
        self,
        client_id: str,
        project_id: str,
        section: Optional[str] = None,
        framework: str = "iso_27001",
    ) -> UnifiedContextProfile:
        """
        Build unified context profile for question generation.

        Args:
            client_id: Client UUID
            project_id: Project UUID
            section: Optional section ID (e.g., "A.5") for relevant chunk retrieval
            framework: Framework type (iso_27001 or bnm_rmit)

        Returns:
            UnifiedContextProfile with all aggregated context
        """
        # 1. Get organization context from Neo4j
        neo4j_context = await self._neo4j.get_organization_context(
            client_id=client_id, project_id=project_id
        )

        if not neo4j_context:
            logger.warning(
                f"No organization context found for client={client_id}, "
                f"project={project_id}"
            )
            # Return minimal context
            return UnifiedContextProfile(
                organization=OrganizationContext(name="Unknown Organization")
            )

        # 2. Build organization context (includes fields from linked nodes)
        org_context = OrganizationContext(
            name=neo4j_context.get("name", "Unknown"),
            industry_type=neo4j_context.get("industry_type"),
            industry_sector=neo4j_context.get("industry_sector"),  # From Industry node
            nature_of_business=neo4j_context.get("nature_of_business"),
            business_context_summary=neo4j_context.get(
                "business_context_summary"
            ),  # From BusinessContext node
            department=neo4j_context.get("department"),
            department_description=neo4j_context.get(
                "department_description"
            ),  # From Department node
            scope_statement_isms=neo4j_context.get("scope_statement_isms"),
            scope_boundaries=neo4j_context.get("scope_boundaries")
            or [],  # From ISMSScope node
            scope_exclusions=neo4j_context.get("scope_exclusions")
            or [],  # From ISMSScope node
            web_domain=neo4j_context.get("web_domain"),
            uses_context_nodes=neo4j_context.get("uses_context_nodes", False),
        )

        # 3. Build discovered context from linked entities
        discovered = DiscoveredContext()

        # Digital assets
        if neo4j_context.get("digital_assets"):
            for asset in neo4j_context["digital_assets"]:
                if asset.get("url"):
                    discovered.digital_assets.append(
                        DigitalAssetContext(
                            url=asset["url"],
                            asset_type=asset.get("asset_type", "website"),
                            title=asset.get("title"),
                            purpose=asset.get("purpose"),
                            technology_hints=asset.get("technology_hints", []),
                        )
                    )
                    # Aggregate technology hints
                    if asset.get("technology_hints"):
                        discovered.technology_hints.extend(asset["technology_hints"])

        # Deduplicate technology hints
        discovered.technology_hints = list(set(discovered.technology_hints))

        # Services
        if neo4j_context.get("services"):
            for svc in neo4j_context["services"]:
                if svc.get("name"):
                    discovered.services.append(svc["name"])

        # Certifications
        if neo4j_context.get("certifications"):
            for cert in neo4j_context["certifications"]:
                if cert.get("name"):
                    discovered.certifications.append(cert["name"])

        # 4. Build existing policies context
        existing_policies = ExistingPolicies()
        if neo4j_context.get("documents"):
            for doc in neo4j_context["documents"]:
                if doc.get("filename"):
                    existing_policies.policy_summaries.append(
                        DocumentContext(
                            filename=doc["filename"],
                            extraction_type=doc.get("extraction_type"),
                            controls_referenced=doc.get("controls_referenced", []),
                        )
                    )
                    # Aggregate controls addressed
                    if doc.get("controls_referenced"):
                        existing_policies.controls_addressed.extend(
                            doc["controls_referenced"]
                        )

        # Deduplicate controls addressed
        existing_policies.controls_addressed = list(
            set(existing_policies.controls_addressed)
        )

        # 5. Build risk profile based on industry and department
        risk_profile = self._build_risk_profile(
            industry_type=org_context.industry_type,
            department=org_context.department,
            digital_assets=discovered.digital_assets,
            certifications=discovered.certifications,
        )

        # 6. Get relevant document chunks from Qdrant (if section specified)
        relevant_chunks = []
        if section:
            relevant_chunks = await self._get_relevant_chunks(
                project_id=project_id,
                section=section,
                framework=framework,
            )

        return UnifiedContextProfile(
            organization=org_context,
            discovered_context=discovered,
            existing_policies=existing_policies,
            risk_profile=risk_profile,
            relevant_chunks=relevant_chunks,
        )

    def _build_risk_profile(
        self,
        industry_type: Optional[str],
        department: Optional[str],
        digital_assets: list[DigitalAssetContext],
        certifications: list[str],
    ) -> RiskProfile:
        """Build risk profile based on industry, department, and context."""
        # Industry-specific risks
        industry_risks = INDUSTRY_RISKS.get(
            industry_type or "", ["General information security risks"]
        )

        # Department-specific risks and focus areas
        department_risks = DEPARTMENT_RISKS.get(
            department or "", ["General departmental security risks"]
        )
        department_focus = DEPARTMENT_FOCUS.get(department or "", None)

        # Determine asset exposure
        asset_exposure = "low"
        if len(digital_assets) > 5:
            asset_exposure = "high"
        elif len(digital_assets) > 2:
            asset_exposure = "medium"

        # Check for high-risk asset types
        for asset in digital_assets:
            if asset.asset_type in ("api", "portal"):
                asset_exposure = "high"
                break

        # Determine regulatory pressure based on industry
        high_reg_industries = [
            "Banking & Financial Services",
            "Insurance",
            "Capital Markets",
            "Healthcare",
            "Government & Public Sector",
        ]
        regulatory_pressure = (
            "high" if industry_type in high_reg_industries else "medium"
        )

        # Adjust if they have certifications (indicates maturity)
        if certifications:
            # Having certifications doesn't reduce regulatory pressure,
            # but indicates they're taking it seriously
            pass

        return RiskProfile(
            industry_risks=industry_risks,
            department_risks=department_risks,
            department_focus=department_focus,
            asset_exposure=asset_exposure,
            regulatory_pressure=regulatory_pressure,
        )

    async def _get_relevant_chunks(
        self,
        project_id: str,
        section: str,
        framework: str,
        limit: int = 5,
    ) -> list[str]:
        """
        Get relevant document chunks from Qdrant for a section.

        Uses semantic search to find chunks that might be relevant
        to the given framework section.
        """
        try:
            # Build a search query based on section
            section_queries = {
                # ISO 27001 Annex A sections
                "A.5": "information security policies organizational controls",
                "A.6": "people controls screening employment security awareness",
                "A.7": "physical security perimeters entry controls equipment",
                "A.8": "technological controls access authentication encryption logging",
                # Management clauses
                "4": "context organization interested parties ISMS scope",
                "5": "leadership commitment policy roles responsibilities",
                "6": "planning risk assessment objectives changes",
                "7": "support resources competence awareness communication documentation",
                "8": "operation planning control risk assessment treatment",
                "9": "performance evaluation monitoring audit management review",
                "10": "improvement nonconformity corrective action",
            }

            query_text = section_queries.get(section, f"information security {section}")

            # Use Qdrant semantic search
            from app.models.search import SearchRequest

            search_req = SearchRequest(
                query=query_text,
                project_id=project_id,
                limit=limit,
                min_score=0.5,
            )

            results = await self._qdrant.search(search_req)

            # Extract chunk content
            chunks = [r.content for r in results.results if r.content]
            return chunks

        except Exception as e:
            logger.warning(f"Failed to get relevant chunks: {e}")
            return []


# Singleton pattern
_context_aggregator: Optional[ContextAggregator] = None


def get_context_aggregator() -> ContextAggregator:
    """Get cached ContextAggregator instance."""
    global _context_aggregator
    if _context_aggregator is None:
        _context_aggregator = ContextAggregator()
    return _context_aggregator


def reset_context_aggregator() -> None:
    """Reset aggregator for testing."""
    global _context_aggregator
    _context_aggregator = None
