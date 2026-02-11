"""Assessment submission router."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from app.auth.dependencies import get_current_user
from app.models.assessment import (
    AssessmentRequest,
    AssessmentResponse,
    AssessmentSummary,
    DocumentResult,
    IndustryType,
    KnowledgeGraph,
    Neo4jNodeReference,
    OrganizationContextSummary,
    OrganizationInfo,
    WebCrawlSummary,
)
from app.services.assessment_orchestrator import get_orchestrator
from app.services.neo4j_service import get_neo4j_service

router = APIRouter(prefix="/assessment", tags=["assessment"])


def _graph_query_result_to_react_flow_for_findings(raw):
    """Build React Flow KnowledgeGraph from Neo4j graph (used by findings endpoint)."""
    from app.models.assessment import (
        GraphEdge as RFGraphEdge,
        GraphNode as RFGraphNode,
        GraphNodeData,
        GraphNodePosition,
    )

    if not raw or not raw.nodes:
        return KnowledgeGraph(nodes=[], edges=[])
    node_ids = {n.id for n in raw.nodes}
    targets_by_source = {}
    sources_by_target = {}
    for e in raw.edges:
        if e.source not in node_ids or e.target not in node_ids:
            continue
        targets_by_source.setdefault(e.source, []).append(e.target)
        sources_by_target.setdefault(e.target, []).append(e.source)

    level_by_id = {}
    queue = []
    for n in raw.nodes:
        if n.id not in sources_by_target:
            level_by_id[n.id] = 0
            queue.append((n.id, 0))
    if not queue and raw.nodes:
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

    by_level = {}
    for n in raw.nodes:
        lvl = level_by_id[n.id]
        by_level.setdefault(lvl, []).append(n)
    max_level = max(by_level.keys(), default=0)

    COLUMN_GAP = 220
    ROW_GAP = 100
    START_X = 80
    START_Y = 60
    LABEL_TO_RF = {
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

    def display_label(neo4j_label, props):
        p = props or {}
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
            return p.get("title") or (p.get("url") or "")[:40] or "Digital Asset"
        if neo4j_label == "Policy":
            return p.get("title") or "Policy"
        if neo4j_label == "Document":
            return p.get("filename") or "Document"
        if neo4j_label == "ExtractedDocument":
            return p.get("source_filename") or p.get("filename") or "Document"
        if neo4j_label == "Control":
            return p.get("identifier") or p.get("title") or "Control"
        return neo4j_label

    rf_nodes = []
    for level in range(max_level + 1):
        level_nodes = by_level.get(level, [])
        x = START_X + level * COLUMN_GAP
        for i, n in enumerate(level_nodes):
            y = START_Y + i * ROW_GAP
            neo4j_label = n.label if n.label != "Company" else "Organization"
            rf_type = LABEL_TO_RF.get(neo4j_label, "default")
            label = display_label(neo4j_label, n.properties)
            rf_nodes.append(
                RFGraphNode(
                    id=n.id,
                    type=rf_type,
                    position=GraphNodePosition(x=x, y=y),
                    data=GraphNodeData(
                        label=label,
                        node_type=neo4j_label,
                        neo4j_id=n.id,
                        properties=n.properties or {},
                    ),
                )
            )

    rf_edges = []
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


@router.post("/submit", response_model=AssessmentResponse)
async def submit_assessment(
    client_id: str = Form(..., description="Client UUID"),
    project_id: str = Form(..., description="Project UUID"),
    organization_name: str = Form(..., description="Organization name"),
    nature_of_business: str = Form(
        ..., min_length=10, description="Business description (min 10 chars)"
    ),
    industry_type: IndustryType = Form(..., description="Industry classification"),
    department: str = Form(..., description="Requesting department"),
    scope_statement_isms: str = Form(
        ..., min_length=10, description="Scope statement ISMS (min 10 chars)"
    ),
    web_domain: str = Form(None, description="Organization web domain"),
    documents: list[UploadFile] = File(
        default=[], description="Policy documents to analyze (optional)"
    ),
    current_user: dict = Depends(get_current_user),
) -> AssessmentResponse:
    """
    Receive assessment submission.

    Accepts multipart/form-data with:
    - Organization info (form fields)
    - Scope statement ISMS (required)
    - Document files (PDF, DOCX, TXT, XLSX, XLS, CSV) - optional

    Returns acknowledgment with assessment_id for tracking.
    Documents are queued for processing by downstream agents.
    """
    # Validate file types if documents are provided
    if documents:
        allowed_extensions = {".pdf", ".docx", ".doc", ".txt", ".xlsx", ".xls", ".csv"}
        for doc in documents:
            if doc.filename:
                ext = (
                    "." + doc.filename.rsplit(".", 1)[-1].lower()
                    if "." in doc.filename
                    else ""
                )
                if ext not in allowed_extensions:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported file type: {doc.filename}. Allowed: {', '.join(allowed_extensions)}",
                    )

    # Build request from form data
    request = AssessmentRequest(
        client_id=client_id,
        project_id=project_id,
        organization_info=OrganizationInfo(
            organization_name=organization_name,
            nature_of_business=nature_of_business,
            industry_type=industry_type,
            department=department,
            web_domain=web_domain,
            scope_statement_isms=scope_statement_isms,
        ),
    )

    orchestrator = get_orchestrator()
    return await orchestrator.receive_assessment(request, documents or [])


@router.get("/findings", response_model=AssessmentResponse)
async def get_findings_for_project(
    client_id: str = Query(..., description="Client UUID"),
    project_id: str = Query(..., description="Project UUID"),
    current_user: dict = Depends(get_current_user),
) -> AssessmentResponse:
    """
    Get findings (assessment response) for a project from Neo4j and related data.

    Returns the same shape as POST /assessment/submit so the findings page
    can load real data instead of sample JSON. Requires an Organization
    context to exist for this client_id and project_id in Neo4j.
    """
    neo4j = get_neo4j_service()
    ctx = await neo4j.get_organization_context(client_id, project_id)
    if not ctx:
        raise HTTPException(
            status_code=404,
            detail="No assessment context found for this project. Run an assessment first.",
        )

    raw = await neo4j.get_project_graph(project_id)
    knowledge_graph = _graph_query_result_to_react_flow_for_findings(raw)

    org_name = ctx.get("name") or "Organization"
    scope_stmt = ctx.get("scope_statement_isms") or ""
    scope_preview = scope_stmt[:100] + "…" if len(scope_stmt) > 100 else scope_stmt

    org_id = None
    context_nodes: list[Neo4jNodeReference] = []
    context_nodes_created: list[str] = []
    for node in knowledge_graph.nodes:
        if node.type == "organization":
            org_id = node.id
        else:
            nt = node.data.node_type if hasattr(node.data, "node_type") else "Unknown"
            context_nodes.append(
                Neo4jNodeReference(
                    node_id=node.id,
                    node_type=nt,
                    name=getattr(node.data, "label", None) or nt,
                )
            )
            if nt not in context_nodes_created:
                context_nodes_created.append(nt)

    org_context = OrganizationContextSummary(
        created=True,
        organization_id=org_id,
        organization_name=org_name,
        industry_type=ctx.get("industry_type") or "Other",
        industry_sector=ctx.get("industry_sector"),
        department=ctx.get("department") or "",
        scope_statement_preview=scope_preview,
        web_domain=ctx.get("web_domain"),
        context_nodes=context_nodes,
        context_nodes_created=context_nodes_created,
    )

    doc_list = ctx.get("documents") or []
    documents = []
    for i, d in enumerate(doc_list):
        if not d or not d.get("filename"):
            continue
        controls = d.get("controls_referenced") or []
        documents.append(
            DocumentResult(
                document_id=d.get("document_id") or f"doc-{project_id}-{i}",
                filename=d["filename"],
                status="processed",
                extracted_text_length=0,
                findings_count=len(controls),
            )
        )

    # Query Supabase for web crawl results
    web_crawl = None
    try:
        from app.db.supabase import get_async_supabase_client_async

        sb = await get_async_supabase_client_async()
        crawl_response = await (
            sb.table("web_crawl_results")
            .select("*")
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if crawl_response.data:
            row = crawl_response.data[0]
            digital_assets = row.get("digital_assets") or []
            web_crawl = WebCrawlSummary(
                success=True,
                pages_crawled=row.get("pages_crawled", 0),
                digital_assets_found=len(digital_assets),
                business_context_extracted=row.get("business_context") is not None,
                organization_info_extracted=row.get("organization_info") is not None,
                confidence_score=row.get("confidence_score", 0.0),
                errors=[],
                from_cache=False,
                business_context=row.get("business_context"),
                digital_assets=digital_assets,
                organization_info=row.get("organization_info"),
            )
    except Exception:
        pass  # web_crawl stays None if query fails

    # Build highlights from available data
    highlights = []
    if web_crawl:
        highlights.append(f"{web_crawl.pages_crawled} pages crawled")
        highlights.append(f"{web_crawl.digital_assets_found} digital assets discovered")
        if web_crawl.business_context_extracted:
            highlights.append("Business context extracted")
        if web_crawl.organization_info_extracted:
            highlights.append("Organization info extracted")
    if documents:
        highlights.append(f"{len(documents)} documents processed")

    summary = AssessmentSummary(
        headline=f"Assessment for {org_name}",
        processing_time_ms=0,
        highlights=highlights,
        next_step="review_findings",
        next_step_url=f"/clients/{client_id}/projects/{project_id}/findings",
    )

    return AssessmentResponse(
        assessment_id=project_id,
        project_id=project_id,
        documents_received=len(documents),
        status="completed",
        documents=documents,
        web_crawl=web_crawl,
        organization_context=org_context,
        knowledge_graph=knowledge_graph,
        summary=summary,
    )


@router.get("/status/{assessment_id}")
async def get_assessment_status(
    assessment_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Get status of an assessment.

    Returns the current state of the assessment including
    document processing status and any findings.
    """
    orchestrator = get_orchestrator()
    status = await orchestrator.get_assessment_status(assessment_id)
    if not status:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return status
