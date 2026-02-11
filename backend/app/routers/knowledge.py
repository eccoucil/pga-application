"""Knowledge graph API router."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.models.assessment import (
    GraphEdge as RFGraphEdge,
    GraphNode as RFGraphNode,
    GraphNodeData,
    GraphNodePosition,
    KnowledgeGraph,
)
from app.models.knowledge_graph import (
    CompanyNode,
    ComplianceGapResult,
    DigitalAssetNode,
    FrameworkType,
    GraphQueryResult,
    GraphStats,
    PolicyNode,
)
from app.services.neo4j_service import get_neo4j_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

# Left-to-right layout constants (match frontend ContextNodesGraph)
_COLUMN_GAP = 220
_ROW_GAP = 100
_START_X = 80
_START_Y = 60

# Neo4j label -> React Flow type and display node_type (NEO4J_SCHEMA.md)
_LABEL_TO_RF_TYPE = {
    "Organization": "organization",
    "Company": "organization",
    "Industry": "industry",
    "Department": "department",
    "ISMSScope": "scope",
    "BusinessContext": "context",
    "DigitalAsset": "asset",
    "Policy": "policy",
    "Document": "document",
    "ExtractedDocument": "document",
    "Control": "control",
}


def _display_label(neo4j_label: str, properties: dict) -> str:
    """Derive display label from Neo4j node properties (NEO4J_SCHEMA)."""
    p = properties
    if neo4j_label in ("Organization", "Company"):
        return p.get("name") or "Organization"
    if neo4j_label == "Industry":
        return p.get("type") or p.get("sector") or "Industry"
    if neo4j_label == "Department":
        return p.get("name") or "Department"
    if neo4j_label == "ISMSScope":
        st = p.get("statement") or ""
        return (st[:50] + "…") if len(st) > 50 else (st or "ISMSScope")
    if neo4j_label == "BusinessContext":
        return p.get("summary") or p.get("nature_of_business") or "Business Context"
    if neo4j_label == "DigitalAsset":
        return p.get("title") or p.get("url", "")[:40] or "Digital Asset"
    if neo4j_label == "Policy":
        return p.get("title") or "Policy"
    if neo4j_label == "Document":
        return p.get("filename") or "Document"
    if neo4j_label == "ExtractedDocument":
        return p.get("source_filename") or p.get("filename") or "Document"
    if neo4j_label == "Control":
        return p.get("identifier") or p.get("title") or "Control"
    return neo4j_label


def _graph_query_result_to_react_flow(raw: GraphQueryResult) -> KnowledgeGraph:
    """Convert Neo4j GraphQueryResult to React Flow KnowledgeGraph (left-to-right layout)."""
    node_ids = {n.id for n in raw.nodes}
    targets_by_source: dict[str, list[str]] = {}
    sources_by_target: dict[str, list[str]] = {}
    for e in raw.edges:
        if e.source not in node_ids or e.target not in node_ids:
            continue
        targets_by_source.setdefault(e.source, []).append(e.target)
        sources_by_target.setdefault(e.target, []).append(e.source)

    # BFS levels (roots = no incoming)
    level_by_id: dict[str, int] = {}
    queue: list[tuple[str, int]] = []
    for n in raw.nodes:
        if n.id not in sources_by_target:
            level_by_id[n.id] = 0
            queue.append((n.id, 0))
    if not queue:
        if raw.nodes:
            first = raw.nodes[0].id
            level_by_id[first] = 0
            queue.append((first, 0))
    while queue:
        nid, level = queue.pop(0)
        for t in targets_by_source.get(nid, []):
            next_level = level + 1
            if t not in level_by_id or next_level < level_by_id[t]:
                level_by_id[t] = next_level
                queue.append((t, next_level))
    for n in raw.nodes:
        level_by_id.setdefault(n.id, 1)

    # Group by level
    by_level: dict[int, list] = {}
    for n in raw.nodes:
        lvl = level_by_id[n.id]
        by_level.setdefault(lvl, []).append(n)
    max_level = max(by_level.keys(), default=0)

    # Build React Flow nodes with positions
    rf_nodes: list[RFGraphNode] = []
    for level in range(max_level + 1):
        level_nodes = by_level.get(level, [])
        x = _START_X + level * _COLUMN_GAP
        for i, n in enumerate(level_nodes):
            y = _START_Y + i * _ROW_GAP
            neo4j_label = n.label if n.label != "Company" else "Organization"
            rf_type = _LABEL_TO_RF_TYPE.get(neo4j_label, "default")
            node_type = neo4j_label
            label = _display_label(neo4j_label, n.properties or {})
            rf_nodes.append(
                RFGraphNode(
                    id=n.id,
                    type=rf_type,
                    position=GraphNodePosition(x=x, y=y),
                    data=GraphNodeData(
                        label=label,
                        node_type=node_type,
                        neo4j_id=n.id,
                        properties=n.properties or {},
                    ),
                )
            )

    # Build React Flow edges
    rf_edges: list[RFGraphEdge] = []
    for e in raw.edges:
        if e.source not in node_ids or e.target not in node_ids:
            continue
        rf_edges.append(
            RFGraphEdge(
                id=f"e-{e.source}-{e.target}",
                source=e.source,
                target=e.target,
                type="default",
                label=e.relationship,
                animated=False,
            )
        )

    return KnowledgeGraph(nodes=rf_nodes, edges=rf_edges)


@router.get("/graph/{project_id}/react-flow", response_model=KnowledgeGraph)
async def get_project_graph_react_flow(
    project_id: str,
    current_user: dict = Depends(get_current_user),
) -> KnowledgeGraph:
    """
    Get the knowledge graph for a project in React Flow format (NEO4J_SCHEMA).

    Returns nodes and edges with positions for left-to-right visualization
    in the findings stepper. Includes Organization, Industry, Department,
    ISMSScope, BusinessContext, DigitalAsset, Policy, Document, Control.
    """
    neo4j = get_neo4j_service()
    raw = await neo4j.get_project_graph(project_id)
    return _graph_query_result_to_react_flow(raw)


@router.get("/graph/{project_id}", response_model=GraphQueryResult)
async def get_project_graph(
    project_id: str,
    current_user: dict = Depends(get_current_user),
) -> GraphQueryResult:
    """
    Get the full knowledge graph for a project.

    Returns all nodes (Company, Policy, Document, DigitalAsset, Control)
    and relationships within the project scope.
    """
    neo4j = get_neo4j_service()
    return await neo4j.get_project_graph(project_id)


@router.get("/graph/{project_id}/stats", response_model=GraphStats)
async def get_graph_stats(
    project_id: str,
    current_user: dict = Depends(get_current_user),
) -> GraphStats:
    """
    Get statistics about the knowledge graph for a project.

    Returns counts of each node type and total relationships.
    """
    neo4j = get_neo4j_service()
    return await neo4j.get_graph_stats(project_id)


@router.get("/policies/{project_id}", response_model=list[PolicyNode])
async def list_policies(
    project_id: str,
    policy_type: Optional[str] = Query(None, description="Filter by policy type"),
    current_user: dict = Depends(get_current_user),
) -> list[PolicyNode]:
    """
    List all policy documents for a project.

    Optionally filter by policy type (security_policy, acceptable_use, etc.)
    """
    neo4j = get_neo4j_service()
    await neo4j.initialize()

    query = """
    MATCH (p:Policy {project_id: $project_id})
    WHERE $policy_type IS NULL OR p.policy_type = $policy_type
    RETURN p, elementId(p) as id
    ORDER BY p.created_at DESC
    """

    async with neo4j._driver.session() as session:
        result = await session.run(
            query, project_id=project_id, policy_type=policy_type
        )
        records = await result.data()

    policies = []
    for record in records:
        node = record["p"]
        policies.append(
            PolicyNode(
                id=record["id"],
                project_id=node["project_id"],
                document_id=node["document_id"],
                title=node["title"],
                policy_type=node["policy_type"],
                version=node.get("version"),
                chunk_count=node.get("chunk_count", 0),
            )
        )

    return policies


@router.get("/gaps/{project_id}", response_model=list[ComplianceGapResult])
async def get_compliance_gaps(
    project_id: str,
    framework: FrameworkType = Query(..., description="Framework to analyze"),
    current_user: dict = Depends(get_current_user),
) -> list[ComplianceGapResult]:
    """
    Get compliance gaps for a project against a framework.

    Returns a list of controls with their compliance status
    and any identified gaps.
    """
    neo4j = get_neo4j_service()
    return await neo4j.get_compliance_gaps(project_id, framework)


@router.get("/coverage/{project_id}")
async def get_policy_coverage(
    project_id: str,
    framework: FrameworkType = Query(..., description="Framework to analyze"),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Get coverage statistics for a framework.

    Returns counts of compliant, partially compliant, non-compliant,
    and not assessed controls with coverage percentage.
    """
    neo4j = get_neo4j_service()
    return await neo4j.get_policy_coverage(project_id, framework)


@router.get("/assets/{company_id}", response_model=list[DigitalAssetNode])
async def get_digital_assets(
    company_id: str,
    current_user: dict = Depends(get_current_user),
) -> list[DigitalAssetNode]:
    """
    Get all digital assets for a company.

    Returns assets discovered from web crawl including
    subdomains, portals, APIs, and applications.
    """
    neo4j = get_neo4j_service()
    return await neo4j.get_company_assets(company_id)


@router.post("/company", response_model=CompanyNode)
async def create_company(
    company: CompanyNode,
    current_user: dict = Depends(get_current_user),
) -> CompanyNode:
    """
    Create or update a company node in the knowledge graph.

    The company is identified by domain and project_id combination.
    If a company with the same domain exists in the project, it will be updated.
    """
    neo4j = get_neo4j_service()
    return await neo4j.create_company(company)


@router.post("/policy", response_model=PolicyNode)
async def create_policy(
    policy: PolicyNode,
    company_id: Optional[str] = Query(None, description="Company to link policy to"),
    current_user: dict = Depends(get_current_user),
) -> PolicyNode:
    """
    Create a policy node in the knowledge graph.

    Optionally link the policy to a company node.
    """
    neo4j = get_neo4j_service()
    return await neo4j.create_policy(policy, company_id)
