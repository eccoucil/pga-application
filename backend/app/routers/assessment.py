"""Assessment submission router."""

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from app.auth.dependencies import get_current_user
from app.models.assessment import (
    AssessmentDetailResponse,
    AssessmentListResponse,
    AssessmentRecord,
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assessment", tags=["assessment"])


async def _persist_assessment(
    client_id: str,
    project_id: str,
    user_id: str,
    org_info: OrganizationInfo,
    documents_count: int,
    response: AssessmentResponse,
):
    """Persist assessment to Supabase (best-effort, non-fatal)."""
    try:
        from app.db.supabase import get_supabase_client

        sb = get_supabase_client()
        sb.table("assessments").insert(
            {
                "client_id": client_id,
                "project_id": project_id,
                "user_id": user_id,
                "organization_name": org_info.organization_name,
                "nature_of_business": org_info.nature_of_business,
                "industry_type": org_info.industry_type.value,
                "department": org_info.department,
                "scope_statement_isms": org_info.scope_statement_isms,
                "web_domain": org_info.web_domain,
                "status": response.status,
                "documents_count": documents_count,
                "response_snapshot": response.model_dump(mode="json"),
            }
        ).execute()
    except Exception as e:
        logger.warning(f"Failed to persist assessment: {e}")


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
    response = await orchestrator.receive_assessment(request, documents or [])

    # Persist to Supabase (best-effort)
    await _persist_assessment(
        client_id=client_id,
        project_id=project_id,
        user_id=current_user["user_id"],
        org_info=request.organization_info,
        documents_count=len(documents) if documents else 0,
        response=response,
    )

    return response


@router.get("/list", response_model=AssessmentListResponse)
async def list_assessments(
    project_id: str = Query(..., description="Project UUID"),
    client_id: str = Query(..., description="Client UUID"),
    current_user: dict = Depends(get_current_user),
) -> AssessmentListResponse:
    """List all assessments for a project."""
    from app.db.supabase import get_supabase_client

    sb = get_supabase_client()
    result = (
        sb.table("assessments")
        .select(
            "id, version, organization_name, industry_type, department, status, documents_count, created_at"
        )
        .eq("project_id", project_id)
        .eq("client_id", client_id)
        .order("created_at", desc=True)
        .execute()
    )
    records = [AssessmentRecord(**row) for row in (result.data or [])]
    return AssessmentListResponse(assessments=records, total=len(records))


@router.get("/findings", response_model=AssessmentResponse)
async def get_findings_for_project(
    client_id: str = Query(..., description="Client UUID"),
    project_id: str = Query(..., description="Project UUID"),
    current_user: dict = Depends(get_current_user),
) -> AssessmentResponse:
    """
    Get findings (assessment response) for a project from Supabase.

    Returns the same shape as POST /assessment/submit so the findings page
    can load real data. Sources data from assessments, web_crawl_results,
    and project_documents tables.
    """
    from app.db.supabase import get_async_supabase_client_async

    sb = await get_async_supabase_client_async()

    # Check for a persisted assessment response_snapshot first
    assessment_res = await (
        sb.table("assessments")
        .select("response_snapshot")
        .eq("project_id", project_id)
        .eq("client_id", client_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if assessment_res.data and assessment_res.data[0].get("response_snapshot"):
        # Return the cached response snapshot directly
        try:
            return AssessmentResponse(**assessment_res.data[0]["response_snapshot"])
        except Exception:
            pass  # Fall through to build from parts

    # Fetch client info for org context
    client_res = await (
        sb.table("clients").select("name, industry").eq("id", client_id).limit(1).execute()
    )
    if not client_res.data:
        raise HTTPException(
            status_code=404,
            detail="No assessment context found for this project. Run an assessment first.",
        )
    client = client_res.data[0]
    org_name = client.get("name") or "Organization"

    # Fetch project for scope info
    project_res = await (
        sb.table("projects").select("name, framework, description").eq("id", project_id).limit(1).execute()
    )
    project_data = project_res.data[0] if project_res.data else {}

    # Fetch documents
    docs_res = await (
        sb.table("project_documents")
        .select("id, filename, format, word_count")
        .eq("project_id", project_id)
        .execute()
    )
    documents = []
    for i, d in enumerate(docs_res.data or []):
        documents.append(
            DocumentResult(
                document_id=d.get("id") or f"doc-{project_id}-{i}",
                filename=d.get("filename", "unknown"),
                status="processed",
                extracted_text_length=d.get("word_count", 0),
            )
        )

    # Web crawl results
    web_crawl = None
    try:
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
        pass

    # Build org context from available data
    import uuid

    org_id = str(uuid.uuid4())
    context_nodes: list[Neo4jNodeReference] = [
        Neo4jNodeReference(node_id=org_id, node_type="Organization", name=org_name)
    ]
    context_nodes_created = ["Organization"]

    industry_raw = client.get("industry")
    industry = industry_raw or "Other"
    if industry_raw:
        context_nodes.append(
            Neo4jNodeReference(node_id=str(uuid.uuid4()), node_type="Industry", name=industry_raw)
        )
        context_nodes_created.append("Industry")

    org_context = OrganizationContextSummary(
        created=True,
        organization_id=org_id,
        organization_name=org_name,
        industry_type=industry,
        industry_sector=industry,
        department="",
        scope_statement_preview=project_data.get("description", "")[:100],
        web_domain=None,
        context_nodes=context_nodes,
        context_nodes_created=context_nodes_created,
    )

    # Rebuild knowledge graph from orchestrator's builder
    orchestrator = get_orchestrator()
    knowledge_graph = orchestrator._build_knowledge_graph(
        org_context=org_context,
        web_crawl_result=web_crawl,
        doc_results=documents if documents else None,
    )

    # Build highlights
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


@router.get("/detail/{assessment_id}", response_model=AssessmentDetailResponse)
async def get_assessment_detail(
    assessment_id: str,
    current_user: dict = Depends(get_current_user),
) -> AssessmentDetailResponse:
    """Get full assessment detail by ID."""
    from app.db.supabase import get_supabase_client

    sb = get_supabase_client()
    result = (
        sb.table("assessments")
        .select("*")
        .eq("id", assessment_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Assessment not found")
    row = result.data[0]
    return AssessmentDetailResponse(
        id=row["id"],
        version=row["version"],
        organization_name=row["organization_name"],
        nature_of_business=row["nature_of_business"],
        industry_type=row["industry_type"],
        department=row["department"],
        scope_statement_isms=row["scope_statement_isms"],
        web_domain=row.get("web_domain"),
        status=row["status"],
        documents_count=row["documents_count"],
        response_snapshot=row.get("response_snapshot"),
        created_at=row["created_at"],
    )
