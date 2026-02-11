"""Neo4j service for knowledge graph operations."""

import logging
from typing import Optional

from neo4j import AsyncGraphDatabase, AsyncDriver
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.models.knowledge_graph import (
    BusinessContextNode,
    CompanyNode,
    ComplianceGapResult,
    ComplianceLevel,
    ControlNode,
    DepartmentNode,
    DigitalAssetNode,
    FrameworkType,
    GraphEdge,
    GraphNode,
    GraphQueryResult,
    GraphStats,
    IndustryNode,
    ISMSScopeNode,
    OrganizationNode,
    PolicyControlMapping,
    PolicyNode,
)

logger = logging.getLogger(__name__)


def _sanitize_neo4j_properties(props: dict) -> dict:
    """Convert Neo4j temporal types to JSON-serializable Python types."""
    from neo4j.time import DateTime, Date, Time, Duration

    sanitized = {}
    for key, value in props.items():
        if isinstance(value, DateTime):
            sanitized[key] = value.iso_format()
        elif isinstance(value, Date):
            sanitized[key] = value.iso_format()
        elif isinstance(value, Time):
            sanitized[key] = value.iso_format()
        elif isinstance(value, Duration):
            sanitized[key] = str(value)
        elif isinstance(value, list):
            sanitized[key] = [
                v.iso_format()
                if isinstance(v, (DateTime, Date, Time))
                else str(v)
                if isinstance(v, Duration)
                else v
                for v in value
            ]
        else:
            sanitized[key] = value
    return sanitized


class Neo4jService:
    """Service for knowledge graph operations using Neo4j."""

    def __init__(self) -> None:
        settings = get_settings()
        self._driver: Optional[AsyncDriver] = None
        self._uri = settings.neo4j_uri
        self._user = settings.neo4j_user
        self._password = settings.neo4j_password

    async def initialize(self) -> None:
        """Initialize Neo4j connection and create constraints."""
        if self._driver is not None:
            return

        self._driver = AsyncGraphDatabase.driver(
            self._uri,
            auth=(self._user, self._password),
            max_connection_pool_size=50,
        )

        # Verify connectivity
        await self._driver.verify_connectivity()
        logger.info("Neo4j connection established")

        # Create constraints and indexes
        await self._create_constraints()

    async def _create_constraints(self) -> None:
        """Create uniqueness constraints and indexes."""
        constraints = [
            # Uniqueness constraints - using Organization as central entity
            "CREATE CONSTRAINT organization_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE",
            "CREATE CONSTRAINT policy_id IF NOT EXISTS FOR (p:Policy) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT digital_asset_id IF NOT EXISTS FOR (a:DigitalAsset) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT control_id IF NOT EXISTS FOR (c:Control) REQUIRE c.id IS UNIQUE",
            # Context node constraints - Industry is UNIQUE by type (shared across orgs)
            "CREATE CONSTRAINT industry_type IF NOT EXISTS FOR (i:Industry) REQUIRE i.type IS UNIQUE",
            # Indexes for common queries
            "CREATE INDEX org_project IF NOT EXISTS FOR (o:Organization) ON (o.project_id)",
            "CREATE INDEX org_client IF NOT EXISTS FOR (o:Organization) ON (o.client_id)",
            "CREATE INDEX policy_project IF NOT EXISTS FOR (p:Policy) ON (p.project_id)",
            "CREATE INDEX document_project IF NOT EXISTS FOR (d:Document) ON (d.project_id)",
            "CREATE INDEX control_framework IF NOT EXISTS FOR (c:Control) ON (c.framework)",
            # Context node indexes for project-scoped queries
            "CREATE INDEX business_context_project IF NOT EXISTS FOR (b:BusinessContext) ON (b.project_id)",
            "CREATE INDEX department_project IF NOT EXISTS FOR (d:Department) ON (d.project_id)",
            "CREATE INDEX isms_scope_project IF NOT EXISTS FOR (s:ISMSScope) ON (s.project_id)",
        ]

        async with self._driver.session() as session:
            for constraint in constraints:
                try:
                    await session.run(constraint)
                except Exception as e:
                    # Constraint may already exist
                    logger.debug(f"Constraint creation: {e}")

        logger.info("Neo4j constraints and indexes created")

    async def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")

    async def health_check(self) -> dict:
        """Check Neo4j connection health."""
        if not self._driver:
            return {"status": "not_initialized"}

        try:
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 as health")
                record = await result.single()
                if record and record["health"] == 1:
                    return {"status": "healthy"}
                return {"status": "unhealthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    # --- Organization CRUD ---

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def create_organization(
        self, organization: OrganizationNode, create_context_nodes: bool = True
    ) -> OrganizationNode:
        """
        Create or update an Organization node with assessment context.

        Uses client_id + project_id as composite key (MERGE).

        BACKWARD COMPATIBILITY MODE (transitional):
        - Still stores context fields as properties on Organization node
        - Also creates separate context nodes (BusinessContext, Industry, etc.)
        - This allows gradual migration while maintaining compatibility

        Args:
            organization: Organization node data
            create_context_nodes: If True (default), also create separate context nodes

        Returns:
            Created/updated OrganizationNode with id populated
        """
        await self.initialize()

        # PHASE 1: Create Organization with properties (backward compatibility)
        query = """
        MERGE (o:Organization {client_id: $client_id, project_id: $project_id})
        ON CREATE SET o.created_at = datetime($created_at)
        SET o.name = $name,
            o.web_domain = COALESCE($web_domain, o.web_domain),
            o.nature_of_business = COALESCE($nature_of_business, o.nature_of_business),
            o.industry_type = COALESCE($industry_type, o.industry_type),
            o.department = COALESCE($department, o.department),
            o.scope_statement_isms = COALESCE($scope_statement_isms, o.scope_statement_isms),
            o.description = COALESCE($description, o.description),
            o.headquarters_location = COALESCE($headquarters_location, o.headquarters_location),
            o.updated_at = datetime()
        RETURN elementId(o) as id
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                client_id=organization.client_id,
                project_id=organization.project_id,
                name=organization.name,
                web_domain=organization.web_domain,
                nature_of_business=organization.nature_of_business,
                industry_type=organization.industry_type,
                department=organization.department,
                scope_statement_isms=organization.scope_statement_isms,
                description=organization.description,
                headquarters_location=organization.headquarters_location,
                created_at=organization.created_at.isoformat(),
            )
            record = await result.single()
            organization.id = record["id"]

        # PHASE 2: Also create separate context nodes (new architecture)
        if create_context_nodes and organization.id:
            await self.create_organization_context(
                organization_id=organization.id,
                project_id=organization.project_id,
                nature_of_business=organization.nature_of_business,
                industry_type=organization.industry_type,
                department=organization.department,
                scope_statement_isms=organization.scope_statement_isms,
            )

        return organization

    # Backward compatibility alias
    async def create_company(self, company: CompanyNode) -> CompanyNode:
        """Alias for create_organization (backward compatibility)."""
        return await self.create_organization(company)

    async def get_organization(
        self, project_id: str, client_id: str
    ) -> Optional[OrganizationNode]:
        """Get an Organization by project and client_id with all context fields."""
        await self.initialize()

        query = """
        MATCH (o:Organization {project_id: $project_id, client_id: $client_id})
        RETURN o, elementId(o) as id
        """

        async with self._driver.session() as session:
            result = await session.run(
                query, project_id=project_id, client_id=client_id
            )
            record = await result.single()

            if not record:
                return None

            node = record["c"] if "c" in record else record["o"]
            return OrganizationNode(
                id=record["id"],
                client_id=node["client_id"],
                project_id=node["project_id"],
                name=node["name"],
                web_domain=node.get("web_domain") or node.get("domain"),
                nature_of_business=node.get("nature_of_business"),
                industry_type=node.get("industry_type") or node.get("industry"),
                department=node.get("department"),
                scope_statement_isms=node.get("scope_statement_isms"),
                description=node.get("description"),
                headquarters_location=node.get("headquarters_location"),
            )

    # Backward compatibility alias
    async def get_company(
        self, project_id: str, client_id: str, domain: Optional[str] = None
    ) -> Optional[CompanyNode]:
        """Alias for get_organization (backward compatibility)."""
        return await self.get_organization(project_id, client_id)

    # --- Context Node CRUD (BusinessContext, Industry, Department, ISMSScope) ---

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def create_business_context(
        self, context: BusinessContextNode, organization_id: str
    ) -> BusinessContextNode:
        """
        Create a BusinessContext node linked to an Organization.

        Uses MERGE to update existing context for the same project.
        """
        await self.initialize()

        query = """
        MATCH (o:Organization) WHERE elementId(o) = $organization_id
        MERGE (b:BusinessContext {project_id: $project_id})
        SET b.nature_of_business = $nature_of_business,
            b.summary = $summary,
            b.created_at = datetime($created_at)
        MERGE (o)-[:HAS_BUSINESS_CONTEXT]->(b)
        RETURN elementId(b) as id
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                organization_id=organization_id,
                project_id=context.project_id,
                nature_of_business=context.nature_of_business,
                summary=context.summary,
                created_at=context.created_at.isoformat(),
            )
            record = await result.single()
            context.id = record["id"]

        return context

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def create_industry(self, industry: IndustryNode) -> IndustryNode:
        """
        Create or get an Industry node (SHARED across organizations).

        Uses MERGE by industry type to ensure reuse.
        Returns existing node if type already exists.
        """
        await self.initialize()

        query = """
        MERGE (i:Industry {type: $type})
        ON CREATE SET i.sector = $sector,
                      i.description = $description
        RETURN elementId(i) as id
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                type=industry.type,
                sector=industry.sector,
                description=industry.description,
            )
            record = await result.single()
            industry.id = record["id"]

        return industry

    async def link_organization_to_industry(
        self, organization_id: str, industry_id: str
    ) -> None:
        """Link an Organization to an Industry node."""
        await self.initialize()

        query = """
        MATCH (o:Organization) WHERE elementId(o) = $organization_id
        MATCH (i:Industry) WHERE elementId(i) = $industry_id
        MERGE (o)-[:IN_INDUSTRY]->(i)
        """

        async with self._driver.session() as session:
            await session.run(
                query,
                organization_id=organization_id,
                industry_id=industry_id,
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def create_department(
        self, department: DepartmentNode, organization_id: str
    ) -> DepartmentNode:
        """
        Create a Department node linked to an Organization.

        Uses MERGE to update existing department for the same project.
        """
        await self.initialize()

        query = """
        MATCH (o:Organization) WHERE elementId(o) = $organization_id
        MERGE (d:Department {project_id: $project_id, name: $name})
        SET d.description = $description,
            d.created_at = datetime($created_at)
        MERGE (o)-[:HAS_DEPARTMENT]->(d)
        RETURN elementId(d) as id
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                organization_id=organization_id,
                project_id=department.project_id,
                name=department.name,
                description=department.description,
                created_at=department.created_at.isoformat(),
            )
            record = await result.single()
            department.id = record["id"]

        return department

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def create_isms_scope(
        self, scope: ISMSScopeNode, organization_id: str
    ) -> ISMSScopeNode:
        """
        Create an ISMSScope node linked to an Organization.

        Uses MERGE to update existing scope for the same project.
        """
        await self.initialize()

        query = """
        MATCH (o:Organization) WHERE elementId(o) = $organization_id
        MERGE (s:ISMSScope {project_id: $project_id})
        SET s.statement = $statement,
            s.boundaries = $boundaries,
            s.exclusions = $exclusions,
            s.created_at = datetime($created_at)
        MERGE (o)-[:HAS_SCOPE]->(s)
        RETURN elementId(s) as id
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                organization_id=organization_id,
                project_id=scope.project_id,
                statement=scope.statement,
                boundaries=scope.boundaries,
                exclusions=scope.exclusions,
                created_at=scope.created_at.isoformat(),
            )
            record = await result.single()
            scope.id = record["id"]

        return scope

    async def create_organization_context(
        self,
        organization_id: str,
        project_id: str,
        nature_of_business: Optional[str] = None,
        industry_type: Optional[str] = None,
        department: Optional[str] = None,
        scope_statement_isms: Optional[str] = None,
    ) -> dict:
        """
        Create all context nodes for an organization in a single call.

        This is a convenience method that creates BusinessContext, Industry,
        Department, and ISMSScope nodes and links them to the Organization.

        Returns:
            Dict with created node IDs
        """
        result = {}

        # Create BusinessContext if nature_of_business provided
        if nature_of_business:
            context = BusinessContextNode(
                project_id=project_id,
                nature_of_business=nature_of_business,
            )
            created = await self.create_business_context(context, organization_id)
            result["business_context_id"] = created.id

        # Create/link Industry if industry_type provided
        if industry_type:
            # Determine sector from industry type
            sector = self._get_industry_sector(industry_type)
            industry = IndustryNode(type=industry_type, sector=sector)
            created = await self.create_industry(industry)
            await self.link_organization_to_industry(organization_id, created.id)
            result["industry_id"] = created.id

        # Create Department if department provided
        if department:
            dept = DepartmentNode(project_id=project_id, name=department)
            created = await self.create_department(dept, organization_id)
            result["department_id"] = created.id

        # Create ISMSScope if scope_statement_isms provided
        if scope_statement_isms:
            scope = ISMSScopeNode(
                project_id=project_id,
                statement=scope_statement_isms,
            )
            created = await self.create_isms_scope(scope, organization_id)
            result["isms_scope_id"] = created.id

        return result

    def _get_industry_sector(self, industry_type: str) -> Optional[str]:
        """Map industry type to broader sector classification."""
        sector_mapping = {
            "Banking & Financial Services": "Financial Services",
            "Insurance": "Financial Services",
            "Capital Markets": "Financial Services",
            "Healthcare": "Healthcare & Life Sciences",
            "Government & Public Sector": "Public Sector",
            "Manufacturing": "Industrial",
            "Technology & Software": "Technology",
            "Telecommunications": "Technology",
            "Retail & E-commerce": "Consumer",
            "Energy & Utilities": "Energy",
            "Education": "Public Sector",
        }
        return sector_mapping.get(industry_type)

    # --- Policy CRUD ---

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def create_policy(
        self, policy: PolicyNode, organization_id: Optional[str] = None
    ) -> PolicyNode:
        """Create a policy node, optionally linked to an Organization."""
        await self.initialize()

        query = """
        MERGE (p:Policy {document_id: $document_id})
        SET p.project_id = $project_id,
            p.title = $title,
            p.policy_type = $policy_type,
            p.version = $version,
            p.effective_date = $effective_date,
            p.chunk_count = $chunk_count,
            p.created_at = datetime($created_at)
        RETURN elementId(p) as id
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                document_id=policy.document_id,
                project_id=policy.project_id,
                title=policy.title,
                policy_type=policy.policy_type.value,
                version=policy.version,
                effective_date=policy.effective_date.isoformat()
                if policy.effective_date
                else None,
                chunk_count=policy.chunk_count,
                created_at=policy.created_at.isoformat(),
            )
            record = await result.single()
            policy.id = record["id"]

            # Link to Organization if provided
            if organization_id:
                await session.run(
                    """
                    MATCH (p:Policy) WHERE elementId(p) = $policy_id
                    MATCH (o:Organization) WHERE elementId(o) = $organization_id
                    MERGE (o)-[:HAS_POLICY]->(p)
                    """,
                    policy_id=policy.id,
                    organization_id=organization_id,
                )

        return policy

    # --- Digital Asset CRUD ---

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def create_digital_asset(
        self, asset: DigitalAssetNode, organization_id: str
    ) -> DigitalAssetNode:
        """Create a digital asset node linked to an Organization."""
        await self.initialize()

        query = """
        MATCH (o:Organization) WHERE elementId(o) = $organization_id
        MERGE (a:DigitalAsset {url: $url, project_id: $project_id})
        SET a.asset_type = $asset_type,
            a.title = $title,
            a.description = $description,
            a.purpose = $purpose,
            a.technology_hints = $technology_hints,
            a.discovered_at = datetime($discovered_at)
        MERGE (o)-[:HAS_ASSET]->(a)
        RETURN elementId(a) as id
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                organization_id=organization_id,
                url=asset.url,
                project_id=asset.project_id,
                asset_type=asset.asset_type.value,
                title=asset.title,
                description=asset.description,
                purpose=asset.purpose,
                technology_hints=asset.technology_hints or [],
                discovered_at=asset.discovered_at.isoformat(),
            )
            record = await result.single()
            asset.id = record["id"]

        return asset

    async def get_organization_assets(
        self, organization_id: str
    ) -> list[DigitalAssetNode]:
        """Get all digital assets for an Organization."""
        await self.initialize()

        query = """
        MATCH (o:Organization)-[:HAS_ASSET]->(a:DigitalAsset)
        WHERE elementId(o) = $organization_id
        RETURN a, elementId(a) as id
        """

        async with self._driver.session() as session:
            result = await session.run(query, organization_id=organization_id)
            records = await result.data()

        assets = []
        for record in records:
            node = record["a"]
            assets.append(
                DigitalAssetNode(
                    id=record["id"],
                    project_id=node["project_id"],
                    organization_id=organization_id,
                    url=node["url"],
                    asset_type=node["asset_type"],
                    title=node.get("title"),
                    description=node.get("description"),
                    purpose=node.get("purpose"),
                    technology_hints=node.get("technology_hints", []),
                )
            )

        return assets

    # Backward compatibility alias
    async def get_company_assets(self, company_id: str) -> list[DigitalAssetNode]:
        """Alias for get_organization_assets (backward compatibility)."""
        return await self.get_organization_assets(company_id)

    # --- Control Mapping ---

    async def link_policy_to_control(self, mapping: PolicyControlMapping) -> None:
        """Create or update a policy-to-control relationship."""
        await self.initialize()

        query = """
        MATCH (p:Policy) WHERE elementId(p) = $policy_id
        MATCH (c:Control) WHERE elementId(c) = $control_id
        MERGE (p)-[r:ADDRESSES]->(c)
        SET r.compliance_level = $compliance_level,
            r.evidence = $evidence,
            r.gap_description = $gap_description,
            r.assessed_at = datetime($assessed_at)
        """

        async with self._driver.session() as session:
            await session.run(
                query,
                policy_id=mapping.policy_id,
                control_id=mapping.control_id,
                compliance_level=mapping.compliance_level.value,
                evidence=mapping.evidence,
                gap_description=mapping.gap_description,
                assessed_at=mapping.assessed_at.isoformat(),
            )

    async def link_document_to_policy(self, doc_id: str, policy_id: str) -> None:
        """Create a DERIVED_POLICY relationship from ExtractedDocument to Policy."""
        await self.initialize()

        query = """
        MATCH (d:ExtractedDocument) WHERE elementId(d) = $doc_id
        MATCH (p:Policy) WHERE elementId(p) = $policy_id
        MERGE (d)-[:DERIVED_POLICY]->(p)
        """

        async with self._driver.session() as session:
            await session.run(query, doc_id=doc_id, policy_id=policy_id)

    async def create_control(self, control: ControlNode) -> ControlNode:
        """Create or get a control node."""
        await self.initialize()

        query = """
        MERGE (c:Control {framework: $framework, identifier: $identifier})
        SET c.title = $title,
            c.description = $description,
            c.category = $category
        RETURN elementId(c) as id
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                framework=control.framework.value,
                identifier=control.identifier,
                title=control.title,
                description=control.description,
                category=control.category,
            )
            record = await result.single()
            control.id = record["id"]

        return control

    # --- Graph Queries ---

    async def get_project_graph(self, project_id: str) -> GraphQueryResult:
        """Get the full knowledge graph for a project."""
        await self.initialize()

        # Query project-scoped nodes + Controls linked via this project's policies
        node_query = """
        MATCH (n)
        WHERE n.project_id = $project_id
        RETURN labels(n) as labels, properties(n) as props, elementId(n) as id
        UNION
        MATCH (p:Policy {project_id: $project_id})-[:ADDRESSES]->(c:Control)
        RETURN labels(c) as labels, properties(c) as props, elementId(c) as id
        """

        # Query all relationships
        edge_query = """
        MATCH (a)-[r]->(b)
        WHERE a.project_id = $project_id OR b.project_id = $project_id
        RETURN elementId(a) as source, elementId(b) as target,
               type(r) as rel_type, properties(r) as props
        """

        nodes = []
        edges = []

        async with self._driver.session() as session:
            # Get nodes
            result = await session.run(node_query, project_id=project_id)
            records = await result.data()
            for record in records:
                nodes.append(
                    GraphNode(
                        id=record["id"],
                        label=record["labels"][0] if record["labels"] else "Unknown",
                        properties=_sanitize_neo4j_properties(record["props"]),
                    )
                )

            # Get edges
            result = await session.run(edge_query, project_id=project_id)
            records = await result.data()
            for record in records:
                edges.append(
                    GraphEdge(
                        source=record["source"],
                        target=record["target"],
                        relationship=record["rel_type"],
                        properties=_sanitize_neo4j_properties(record["props"] or {}),
                    )
                )

        return GraphQueryResult(
            nodes=nodes,
            edges=edges,
            node_count=len(nodes),
            edge_count=len(edges),
        )

    async def get_compliance_gaps(
        self, project_id: str, framework: FrameworkType
    ) -> list[ComplianceGapResult]:
        """Get compliance gaps for a project and framework."""
        await self.initialize()

        query = """
        MATCH (c:Control {framework: $framework})
        OPTIONAL MATCH (p:Policy {project_id: $project_id})-[r:ADDRESSES]->(c)
        RETURN c, elementId(c) as control_id,
               collect({
                   policy_id: elementId(p),
                   compliance_level: r.compliance_level,
                   gap_description: r.gap_description
               }) as mappings
        """

        async with self._driver.session() as session:
            result = await session.run(
                query, project_id=project_id, framework=framework.value
            )
            records = await result.data()

        gaps = []
        for record in records:
            control_node = record["c"]
            mappings = record["mappings"]

            # Determine overall compliance level
            compliance_levels = [
                m["compliance_level"]
                for m in mappings
                if m["compliance_level"] is not None
            ]

            if not compliance_levels:
                overall_level = ComplianceLevel.NOT_ASSESSED
            elif all(cl == "compliant" for cl in compliance_levels):
                overall_level = ComplianceLevel.COMPLIANT
            elif any(cl == "non_compliant" for cl in compliance_levels):
                overall_level = ComplianceLevel.NON_COMPLIANT
            else:
                overall_level = ComplianceLevel.PARTIALLY_COMPLIANT

            # Collect gap descriptions
            gap_desc = next(
                (m["gap_description"] for m in mappings if m["gap_description"]),
                None,
            )

            # Collect covering policy IDs
            covering_policies = [
                m["policy_id"] for m in mappings if m["policy_id"] is not None
            ]

            gaps.append(
                ComplianceGapResult(
                    control=ControlNode(
                        id=record["control_id"],
                        framework=framework,
                        identifier=control_node["identifier"],
                        title=control_node["title"],
                        description=control_node.get("description"),
                        category=control_node.get("category"),
                    ),
                    compliance_level=overall_level,
                    covering_policies=covering_policies,
                    gap_description=gap_desc,
                    recommendations=[],  # Would be populated by analysis
                )
            )

        return gaps

    async def get_policy_coverage(
        self, project_id: str, framework: FrameworkType
    ) -> dict:
        """Get coverage statistics for a framework."""
        await self.initialize()

        query = """
        MATCH (c:Control {framework: $framework})
        OPTIONAL MATCH (p:Policy {project_id: $project_id})-[r:ADDRESSES]->(c)
        RETURN
            count(DISTINCT c) as total_controls,
            count(DISTINCT CASE WHEN r IS NOT NULL THEN c END) as addressed_controls,
            count(DISTINCT CASE WHEN r.compliance_level = 'compliant' THEN c END) as compliant_controls,
            count(DISTINCT CASE WHEN r.compliance_level = 'partially_compliant' THEN c END) as partial_controls,
            count(DISTINCT CASE WHEN r.compliance_level = 'non_compliant' THEN c END) as non_compliant_controls
        """

        async with self._driver.session() as session:
            result = await session.run(
                query, project_id=project_id, framework=framework.value
            )
            record = await result.single()

        total = record["total_controls"] or 0
        addressed = record["addressed_controls"] or 0

        return {
            "framework": framework.value,
            "total_controls": total,
            "addressed_controls": addressed,
            "compliant_controls": record["compliant_controls"] or 0,
            "partially_compliant_controls": record["partial_controls"] or 0,
            "non_compliant_controls": record["non_compliant_controls"] or 0,
            "not_assessed_controls": total - addressed,
            "coverage_percentage": (addressed / total * 100) if total > 0 else 0,
        }

    async def get_graph_stats(self, project_id: str) -> GraphStats:
        """Get graph statistics for a project."""
        await self.initialize()

        query = """
        MATCH (n)
        WHERE n.project_id = $project_id
        WITH labels(n)[0] as label, count(*) as cnt
        RETURN collect({label: label, count: cnt}) as node_counts
        """

        rel_query = """
        MATCH (a)-[r]->(b)
        WHERE a.project_id = $project_id OR b.project_id = $project_id
        RETURN count(r) as rel_count
        """

        async with self._driver.session() as session:
            result = await session.run(query, project_id=project_id)
            record = await result.single()
            node_counts = {
                item["label"]: item["count"]
                for item in record["node_counts"]
                if item["label"]
            }

            result = await session.run(rel_query, project_id=project_id)
            rel_record = await result.single()

        return GraphStats(
            project_id=project_id,
            company_count=node_counts.get("Company", 0)
            + node_counts.get("Organization", 0),
            policy_count=node_counts.get("Policy", 0),
            document_count=node_counts.get("Document", 0)
            + node_counts.get("ExtractedDocument", 0),
            digital_asset_count=node_counts.get("DigitalAsset", 0),
            control_count=node_counts.get("Control", 0),
            # Context node counts
            business_context_count=node_counts.get("BusinessContext", 0),
            industry_count=node_counts.get("Industry", 0),
            department_count=node_counts.get("Department", 0),
            isms_scope_count=node_counts.get("ISMSScope", 0),
            total_nodes=sum(node_counts.values()),
            total_relationships=rel_record["rel_count"] or 0,
        )

    # --- Extracted Document Operations ---

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def create_extracted_document(
        self,
        project_id: str,
        client_id: str,
        document_id: str,
        extraction_type: str,
        extracted_data: dict,
        source_filename: str,
        organization_name: str,
        controls_referenced: Optional[list[str]] = None,
    ) -> str:
        """
        Create ExtractedDocument node linked to Organization.

        Creates Organization node if it doesn't exist.

        Args:
            project_id: Project UUID
            client_id: Client UUID (links to Organization)
            document_id: Unique document identifier
            extraction_type: Type of extraction (inferred/generic)
            extracted_data: Extracted data dictionary
            source_filename: Original filename
            organization_name: Organization name from assessment
            controls_referenced: List of control IDs referenced in document

        Returns:
            Neo4j element ID of created document node
        """
        await self.initialize()

        # Flatten extracted_data for Neo4j (it doesn't handle nested dicts well)
        flat_data = {}
        for key, value in extracted_data.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                flat_data[key] = value
            elif isinstance(value, list):
                # Store lists as JSON strings
                import json

                flat_data[key] = json.dumps(value)
            elif isinstance(value, dict):
                import json

                flat_data[key] = json.dumps(value)

        query = """
        // Get or create Organization for this client
        MERGE (o:Organization {client_id: $client_id, project_id: $project_id})
        ON CREATE SET o.name = $organization_name, o.created_at = datetime()

        // Create ExtractedDocument linked to Organization
        MERGE (d:ExtractedDocument {document_id: $document_id, project_id: $project_id})
        SET d.extraction_type = $extraction_type,
            d.source_filename = $source_filename,
            d.controls_referenced = $controls_referenced,
            d.extracted_at = datetime(),
            d.client_id = $client_id

        // Link document to organization
        MERGE (o)-[:HAS_DOCUMENT]->(d)

        RETURN elementId(d) as doc_id, elementId(o) as organization_id
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                client_id=client_id,
                project_id=project_id,
                document_id=document_id,
                extraction_type=extraction_type,
                source_filename=source_filename,
                organization_name=organization_name,
                controls_referenced=controls_referenced or [],
            )
            record = await result.single()
            doc_id = record["doc_id"]

            # Set extracted data properties separately (to handle dynamic keys)
            if flat_data:
                set_clause = ", ".join(f"d.{key} = ${key}" for key in flat_data.keys())
                update_query = f"""
                MATCH (d:ExtractedDocument) WHERE elementId(d) = $doc_id
                SET {set_clause}
                """
                await session.run(update_query, doc_id=doc_id, **flat_data)

        return doc_id

    async def get_organization_documents(
        self, client_id: str, project_id: str
    ) -> list[dict]:
        """Get all extracted documents for an Organization."""
        await self.initialize()

        query = """
        MATCH (o:Organization {client_id: $client_id, project_id: $project_id})
              -[:HAS_DOCUMENT]->(d:ExtractedDocument)
        RETURN d, elementId(d) as id
        ORDER BY d.extracted_at DESC
        """

        async with self._driver.session() as session:
            result = await session.run(
                query, client_id=client_id, project_id=project_id
            )
            records = await result.data()

        return [{"id": r["id"], **dict(r["d"])} for r in records]

    # Backward compatibility alias
    async def get_company_documents(
        self, client_id: str, project_id: str
    ) -> list[dict]:
        """Alias for get_organization_documents (backward compatibility)."""
        return await self.get_organization_documents(client_id, project_id)

    async def link_extracted_to_control(
        self,
        extracted_doc_id: str,
        control_identifier: str,
        framework: str,
    ) -> None:
        """Link extracted document to a compliance control."""
        await self.initialize()

        query = """
        MATCH (d:ExtractedDocument) WHERE elementId(d) = $doc_id
        MATCH (c:Control {identifier: $identifier, framework: $framework})
        MERGE (d)-[:REFERENCES]->(c)
        """

        async with self._driver.session() as session:
            await session.run(
                query,
                doc_id=extracted_doc_id,
                identifier=control_identifier,
                framework=framework,
            )

    # --- Context Aggregation for Question Generation ---

    async def get_organization_context(
        self, client_id: str, project_id: str
    ) -> Optional[dict]:
        """
        Get full organization context with all linked data for question generation.

        Returns a unified context profile including:
        - Organization core fields (name, web_domain)
        - Context from relationship-traversed nodes (preferred) OR properties (fallback)
        - Digital assets (URLs, types, technologies)
        - Extracted documents with controls_referenced
        - Services and certifications (if available)

        BACKWARD COMPATIBILITY: Reads from new context nodes first (via relationships),
        falls back to Organization properties if context nodes don't exist.

        This is the primary method for building the context profile used in
        contextual question generation.
        """
        await self.initialize()

        # Query with both relationship-based nodes AND property fallbacks
        # Uses subqueries (CALL {}) to collect related entities separately
        # This avoids implicit grouping issues with Neo4j aggregation
        query = """
        MATCH (o:Organization {client_id: $client_id, project_id: $project_id})

        // New relationship-based context nodes
        OPTIONAL MATCH (o)-[:HAS_BUSINESS_CONTEXT]->(bc:BusinessContext)
        OPTIONAL MATCH (o)-[:HAS_DEPARTMENT]->(dept:Department)
        OPTIONAL MATCH (o)-[:HAS_SCOPE]->(scope:ISMSScope)

        // Collect related entities using subqueries to avoid grouping issues
        CALL {
            WITH o
            OPTIONAL MATCH (o)-[:HAS_ASSET]->(a:DigitalAsset)
            RETURN collect(DISTINCT CASE WHEN a IS NOT NULL THEN {
                url: a.url,
                asset_type: a.asset_type,
                title: a.title,
                purpose: a.purpose,
                technology_hints: a.technology_hints
            } END) as digital_assets
        }
        CALL {
            WITH o
            OPTIONAL MATCH (o)-[:HAS_DOCUMENT]->(d:ExtractedDocument)
            RETURN collect(DISTINCT CASE WHEN d IS NOT NULL THEN {
                filename: d.source_filename,
                extraction_type: d.extraction_type,
                controls_referenced: d.controls_referenced
            } END) as documents
        }
        CALL {
            WITH o
            OPTIONAL MATCH (o)-[:HAS_SERVICE]->(s:Service)
            RETURN collect(DISTINCT CASE WHEN s IS NOT NULL THEN {
                name: s.name,
                description: s.description
            } END) as services
        }
        CALL {
            WITH o
            OPTIONAL MATCH (o)-[:HAS_CERTIFICATION]->(c:Certification)
            RETURN collect(DISTINCT CASE WHEN c IS NOT NULL THEN {
                name: c.name,
                valid_until: c.valid_until
            } END) as certifications
        }
        CALL {
            WITH o
            OPTIONAL MATCH (o)-[:IN_INDUSTRY]->(i:Industry)
            RETURN collect(DISTINCT i) as industries
        }

        RETURN {
          name: o.name,
          web_domain: o.web_domain,
          description: o.description,
          headquarters_location: o.headquarters_location,
          nature_of_business: COALESCE(bc.nature_of_business, o.nature_of_business),
          business_context_summary: bc.summary,
          industry_type: COALESCE(industries[0].type, o.industry_type),
          industry_sector: industries[0].sector,
          department: COALESCE(dept.name, o.department),
          department_description: dept.description,
          scope_statement_isms: COALESCE(scope.statement, o.scope_statement_isms),
          scope_boundaries: scope.boundaries,
          scope_exclusions: scope.exclusions,
          uses_context_nodes: bc IS NOT NULL OR size(industries) > 0,
          digital_assets: digital_assets,
          documents: documents,
          services: services,
          certifications: certifications
        } as context
        """

        async with self._driver.session() as session:
            result = await session.run(
                query, client_id=client_id, project_id=project_id
            )
            record = await result.single()

            if not record:
                return None

            context = record["context"]

            # Filter out null/empty entries from collections
            # (CASE WHEN returns null for non-matching rows)
            if context.get("digital_assets"):
                context["digital_assets"] = [
                    a for a in context["digital_assets"] if a and a.get("url")
                ]
            if context.get("documents"):
                context["documents"] = [
                    d for d in context["documents"] if d and d.get("filename")
                ]
            if context.get("services"):
                context["services"] = [
                    s for s in context["services"] if s and s.get("name")
                ]
            if context.get("certifications"):
                context["certifications"] = [
                    c for c in context["certifications"] if c and c.get("name")
                ]

            return context

    async def create_service(
        self,
        client_id: str,
        project_id: str,
        name: str,
        description: Optional[str] = None,
    ) -> str:
        """Create a Service node linked to Organization."""
        await self.initialize()

        query = """
        MATCH (o:Organization {client_id: $client_id, project_id: $project_id})
        MERGE (s:Service {name: $name, project_id: $project_id})
        SET s.description = $description
        MERGE (o)-[:HAS_SERVICE]->(s)
        RETURN elementId(s) as id
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                client_id=client_id,
                project_id=project_id,
                name=name,
                description=description,
            )
            record = await result.single()
            return record["id"]

    async def create_certification(
        self,
        client_id: str,
        project_id: str,
        name: str,
        valid_until: Optional[str] = None,
    ) -> str:
        """Create a Certification node linked to Organization."""
        await self.initialize()

        query = """
        MATCH (o:Organization {client_id: $client_id, project_id: $project_id})
        MERGE (c:Certification {name: $name, project_id: $project_id})
        SET c.valid_until = $valid_until
        MERGE (o)-[:HAS_CERTIFICATION]->(c)
        RETURN elementId(c) as id
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                client_id=client_id,
                project_id=project_id,
                name=name,
                valid_until=valid_until,
            )
            record = await result.single()
            return record["id"]


# Singleton pattern
_neo4j_service: Optional[Neo4jService] = None


def get_neo4j_service() -> Neo4jService:
    """Get cached Neo4j service instance."""
    global _neo4j_service
    if _neo4j_service is None:
        _neo4j_service = Neo4jService()
    return _neo4j_service


def reset_neo4j_service() -> None:
    """Reset service for testing."""
    global _neo4j_service
    _neo4j_service = None
