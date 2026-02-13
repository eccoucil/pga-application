"""
Assessment Orchestrator - Lightweight coordination agent.

NO LLM - pure Python orchestration logic.

Receives the entire payload and prepares it for downstream agents.
Integrates LlamaExtract for document extraction when available.
Runs web crawling in parallel when web_domain is provided.
"""

import asyncio
import logging
import os
import tempfile
import time
import uuid
from typing import Any, Optional

from fastapi import UploadFile

from app.models.assessment import (
    AssessmentRequest,
    AssessmentResponse,
    AssessmentSummary,
    DocumentResult,
    GraphEdge,
    GraphNode,
    GraphNodeData,
    GraphNodePosition,
    KnowledgeGraph,
    Neo4jNodeReference,
    OrganizationContextSummary,
    WebCrawlSummary,
)
from app.models.web_crawler import (
    BusinessContext,
    CrawlRequest,
    CrawlResult,
    DigitalAsset,
    OrganizationInfo,
)

logger = logging.getLogger(__name__)

# Singleton instance
_orchestrator: "AssessmentOrchestrator | None" = None

# Configuration constants
MAX_CONCURRENT_DOCUMENTS = 5
ASSESSMENT_TIMEOUT_SECONDS = 300  # 5 minutes
CACHE_MAX_AGE_DAYS = int(os.environ.get("CACHE_MAX_AGE_DAYS", "7"))


class AssessmentOrchestrator:
    """
    Lightweight orchestrator that:
    1. Receives full payload from /assessment/submit
    2. Validates and structures data
    3. Processes documents with LlamaExtract in parallel (if available)
    4. Runs web crawl in parallel (if web_domain provided)
    5. Stores extractions in Supabase pgvector
    6. Tracks assessment state

    NO LLM calls - pure coordination.
    """

    def __init__(self) -> None:
        self.active_assessments: dict[str, dict] = {}

    async def receive_assessment(
        self,
        request: AssessmentRequest,
        documents: list[UploadFile],
    ) -> AssessmentResponse:
        """
        Entry point - receive, process, and acknowledge assessment payload.

        Runs document processing and web crawling in parallel using asyncio.gather().

        Args:
            request: Assessment request with organization info
            documents: List of uploaded document files

        Returns:
            AssessmentResponse with tracking info and extraction status
        """
        start_time = time.time()
        assessment_id = str(uuid.uuid4())

        # Register assessment
        self.active_assessments[assessment_id] = {
            "request": request.model_dump(),
            "documents": [doc.filename for doc in documents],
            "status": "received",
        }

        # Create Organization node with full context (before parallel tasks)
        # This ensures the Organization exists with all assessment context
        org_context = await self._create_organization_with_context(request)

        # Build parallel tasks
        tasks: list[Any] = []
        task_names: list[str] = []

        # Task 1: Document processing (always)
        tasks.append(
            self._process_documents_parallel(
                documents=documents,
                client_id=request.client_id,
                project_id=request.project_id,
                organization_name=request.organization_info.organization_name,
            )
        )
        task_names.append("documents")

        # Task 2: Web crawl (conditional - only if web_domain provided)
        if request.organization_info.web_domain:
            tasks.append(
                self._run_web_crawl(
                    web_domain=request.organization_info.web_domain,
                    client_id=request.client_id,
                    project_id=request.project_id,
                )
            )
            task_names.append("web_crawl")

        # Execute all tasks in parallel with timeout protection
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=ASSESSMENT_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.error(
                f"Assessment {assessment_id} timed out after {ASSESSMENT_TIMEOUT_SECONDS}s"
            )
            # Return empty/failed results for timed out tasks
            results = [[] if name == "documents" else None for name in task_names]

        # Extract results by task name
        doc_results = self._extract_result(results, task_names, "documents", [])
        web_crawl_tuple = self._extract_result(
            results, task_names, "web_crawl", (None, False)
        )
        # Unpack tuple: (CrawlResult or None, from_cache boolean)
        web_crawl_result, from_cache = web_crawl_tuple

        # Update assessment status
        self.active_assessments[assessment_id]["status"] = "processing"

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        return self._build_response(
            assessment_id=assessment_id,
            request=request,
            doc_results=doc_results,
            web_crawl_result=web_crawl_result,
            from_cache=from_cache,
            org_context=org_context,
            processing_time_ms=processing_time_ms,
        )

    async def _create_organization_with_context(
        self, request: AssessmentRequest
    ) -> OrganizationContextSummary:
        """
        Create organization context from form data for knowledge graph.

        Build organization context from form data (no external DB needed).

        Generates UUID-based node references for the knowledge graph
        visualization. The graph still renders identically — nodes come from
        assessment form data, not from Neo4j.

        Args:
            request: Assessment request containing organization info

        Returns:
            OrganizationContextSummary with context node references
        """
        org_info = request.organization_info
        context_nodes: list[Neo4jNodeReference] = []
        context_nodes_created: list[str] = []

        # Generate context nodes from form data (no Neo4j needed)
        organization_id = str(uuid.uuid4())
        context_nodes.append(
            Neo4jNodeReference(
                node_id=organization_id,
                node_type="Organization",
                name=org_info.organization_name,
            )
        )
        context_nodes_created.append("Organization")

        if org_info.industry_type:
            context_nodes.append(
                Neo4jNodeReference(
                    node_id=str(uuid.uuid4()),
                    node_type="Industry",
                    name=org_info.industry_type.value,
                )
            )
            context_nodes_created.append("Industry")

        if org_info.department:
            context_nodes.append(
                Neo4jNodeReference(
                    node_id=str(uuid.uuid4()),
                    node_type="Department",
                    name=org_info.department,
                )
            )
            context_nodes_created.append("Department")

        if org_info.scope_statement_isms:
            context_nodes.append(
                Neo4jNodeReference(
                    node_id=str(uuid.uuid4()),
                    node_type="ISMSScope",
                    name=None,
                )
            )
            context_nodes_created.append("ISMSScope")

        if org_info.nature_of_business:
            context_nodes.append(
                Neo4jNodeReference(
                    node_id=str(uuid.uuid4()),
                    node_type="BusinessContext",
                    name=None,
                )
            )
            context_nodes_created.append("BusinessContext")

        industry_sector = (
            org_info.industry_type.value if org_info.industry_type else None
        )

        logger.info(
            f"Built Organization context: client={request.client_id}, "
            f"project={request.project_id}, org={org_info.organization_name}, "
            f"nodes={context_nodes_created}"
        )

        return OrganizationContextSummary(
            created=True,
            organization_id=organization_id,
            organization_name=org_info.organization_name,
            industry_type=org_info.industry_type.value
            if org_info.industry_type
            else "Unknown",
            industry_sector=industry_sector,
            department=org_info.department,
            scope_statement_preview=org_info.scope_statement_isms[:100]
            if org_info.scope_statement_isms
            else "",
            web_domain=org_info.web_domain,
            context_nodes=context_nodes,
            context_nodes_created=context_nodes_created,
        )

    def _build_knowledge_graph(
        self,
        org_context: OrganizationContextSummary,
        web_crawl_result: Optional[Any] = None,
        doc_results: Optional[list[DocumentResult]] = None,
        policy_enrichments: Optional[list[dict]] = None,
    ) -> KnowledgeGraph:
        """
        Build React Flow compatible knowledge graph from organization context.

        Positions nodes in a radial layout around the central Organization node.

        Args:
            org_context: Organization context with node references
            web_crawl_result: Optional web crawl result with digital assets

        Returns:
            KnowledgeGraph with nodes and edges for React Flow
        """
        import math

        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        # Central Organization node
        org_node_id = org_context.organization_id or "org-1"
        nodes.append(
            GraphNode(
                id=org_node_id,
                type="organization",
                position=GraphNodePosition(x=400, y=300),
                data=GraphNodeData(
                    label=org_context.organization_name,
                    node_type="Organization",
                    neo4j_id=org_context.organization_id,
                    properties={
                        "industry_type": org_context.industry_type,
                        "department": org_context.department,
                        "web_domain": org_context.web_domain,
                    },
                ),
            )
        )

        # ========== STAR TOPOLOGY: Collect ALL child nodes ==========
        # All non-Organization nodes will be positioned in a single circle
        # Format: (node_id, react_flow_type, label, properties, relationship)
        all_child_nodes: list[tuple[str, str, str, dict, str]] = []

        # Node type mappings
        node_type_map = {
            "Industry": "industry",
            "Department": "department",
            "ISMSScope": "scope",
            "BusinessContext": "context",
        }
        relationship_map = {
            "Industry": "IN_INDUSTRY",
            "Department": "HAS_DEPARTMENT",
            "ISMSScope": "HAS_SCOPE",
            "BusinessContext": "HAS_BUSINESS_CONTEXT",
        }

        # Add context nodes (filter out Organization itself)
        context_nodes = [
            n for n in org_context.context_nodes if n.node_type != "Organization"
        ]
        for ctx_node in context_nodes:
            all_child_nodes.append(
                (
                    ctx_node.node_id,
                    node_type_map.get(ctx_node.node_type, "default"),
                    ctx_node.name or ctx_node.node_type,
                    {"neo4j_id": ctx_node.node_id},
                    relationship_map.get(ctx_node.node_type, "RELATED_TO"),
                )
            )

        # Add digital assets from web crawl if available
        if web_crawl_result and hasattr(web_crawl_result, "digital_assets"):
            assets = web_crawl_result.digital_assets or []
            for i, asset in enumerate(assets[:10]):  # Limit to 10 assets for clarity
                asset_id = f"asset-{i}"
                asset_label = getattr(asset, "description", None) or asset.url[:30]
                asset_type_str = (
                    asset.asset_type.value
                    if hasattr(asset.asset_type, "value")
                    else str(asset.asset_type)
                )
                all_child_nodes.append(
                    (
                        asset_id,
                        "asset",
                        asset_label[:50],
                        {
                            "url": asset.url,
                            "asset_type": asset_type_str,
                            "purpose": getattr(asset, "purpose", None),
                        },
                        "HAS_ASSET",
                    )
                )

        # Add processed documents
        if doc_results:
            for i, doc in enumerate(doc_results):
                if doc.status == "processed":
                    all_child_nodes.append(
                        (
                            f"doc-{i}",
                            "document",
                            (doc.filename[:40] + "…")
                            if len(doc.filename) > 40
                            else doc.filename,
                            {"filename": doc.filename},
                            "HAS_DOCUMENT",
                        )
                    )

        # Add policy nodes from enrichment results
        if policy_enrichments:
            for i, enrichment in enumerate(policy_enrichments):
                if enrichment.get("policy_analysis") == "success":
                    policy_label = enrichment.get("policy_type", "Policy")
                    # Make label more readable
                    display_type = policy_label.replace("_", " ").title()[:30]
                    all_child_nodes.append(
                        (
                            f"policy-{i}",
                            "policy",
                            display_type,
                            {
                                "controls_mapped": enrichment.get("controls_mapped", 0),
                                "policy_type": enrichment.get("policy_type"),
                            },
                            "HAS_POLICY",
                        )
                    )

        # ========== Position ALL child nodes in single circle ==========
        total_children = len(all_child_nodes)
        radius = 250  # Single unified radius for star topology

        for i, (node_id, rf_type, label, props, rel_type) in enumerate(all_child_nodes):
            angle = (2 * math.pi * i) / max(total_children, 1)
            x = 400 + radius * math.cos(angle)
            y = 300 + radius * math.sin(angle)

            # Determine node_type for data based on react flow type
            if rf_type == "asset":
                node_type = "DigitalAsset"
            elif rf_type == "scope":
                node_type = "ISMSScope"
            elif rf_type == "context":
                node_type = "BusinessContext"
            elif rf_type == "document":
                node_type = "Document"
            elif rf_type == "policy":
                node_type = "Policy"
            else:
                node_type = rf_type.capitalize()

            nodes.append(
                GraphNode(
                    id=node_id,
                    type=rf_type,
                    position=GraphNodePosition(x=x, y=y),
                    data=GraphNodeData(
                        label=label,
                        node_type=node_type,
                        neo4j_id=props.get("neo4j_id"),
                        properties={k: v for k, v in props.items() if k != "neo4j_id"},
                    ),
                )
            )

            edges.append(
                GraphEdge(
                    id=f"e-{org_node_id}-{node_id}",
                    source=org_node_id,
                    target=node_id,
                    type="smoothstep",
                    label=rel_type,
                    animated=(rf_type == "asset"),  # Only animate asset edges
                )
            )

        return KnowledgeGraph(nodes=nodes, edges=edges)

    async def _get_cached_crawl_result(
        self,
        project_id: str,
        web_domain: str,
        max_age_days: int = CACHE_MAX_AGE_DAYS,
    ) -> Optional[CrawlResult]:
        """
        Check for cached crawl result in Supabase.

        Args:
            project_id: Project UUID
            web_domain: Domain that was crawled
            max_age_days: Maximum age of cached data (default from CACHE_MAX_AGE_DAYS)

        Returns:
            CrawlResult if valid cache exists, None otherwise
        """
        from datetime import datetime, timedelta, timezone

        from app.db.supabase import get_async_supabase_client_async

        try:
            supabase = await get_async_supabase_client_async()

            # Query for most recent crawl result matching project_id + web_domain
            response = await (
                supabase.table("web_crawl_results")
                .select("*")
                .eq("project_id", project_id)
                .eq("web_domain", web_domain)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            if not response.data:
                logger.debug(
                    f"No cached crawl found for {web_domain} in project {project_id}"
                )
                return None

            row = response.data[0]

            # Check if cache is expired
            created_at_str = row.get("created_at")
            if created_at_str:
                # Parse ISO timestamp (Supabase returns ISO format)
                created_at = datetime.fromisoformat(
                    created_at_str.replace("Z", "+00:00")
                )
                cache_age = datetime.now(timezone.utc) - created_at

                if cache_age > timedelta(days=max_age_days):
                    logger.info(
                        f"Cached crawl for {web_domain} expired "
                        f"(age: {cache_age.days} days, max: {max_age_days} days)"
                    )
                    return None

            # Reconstruct CrawlResult from stored data
            business_context = None
            if row.get("business_context"):
                business_context = BusinessContext(**row["business_context"])

            digital_assets = []
            if row.get("digital_assets"):
                digital_assets = [DigitalAsset(**a) for a in row["digital_assets"]]

            organization_info = None
            if row.get("organization_info"):
                organization_info = OrganizationInfo(**row["organization_info"])

            cached_result = CrawlResult(
                success=True,
                web_domain=row["web_domain"],
                client_id=row["client_id"],
                project_id=row["project_id"],
                pages_crawled=row.get("pages_crawled", 0),
                total_words_analyzed=0,  # Not stored in cache
                business_context=business_context,
                digital_assets=digital_assets,
                organization_info=organization_info,
                confidence_score=row.get("confidence_score", 0.0),
                processing_time_ms=0,  # Not applicable for cached results
                errors=[],
                # Graph data not included in cache (acceptable)
                attack_surface=None,
                graph_company=None,
                graph_assets=[],
            )

            logger.info(
                f"Using cached crawl for {web_domain} "
                f"(created: {created_at_str}, pages: {cached_result.pages_crawled})"
            )
            return cached_result

        except Exception as e:
            logger.warning(f"Failed to check crawl cache: {e}")
            # Return None to fall back to fresh crawl
            return None

    async def _process_documents_parallel(
        self,
        documents: list[UploadFile],
        client_id: str,
        project_id: str,
        organization_name: str,
    ) -> list[DocumentResult]:
        """
        Process documents in parallel with concurrency limit.

        Uses a semaphore to prevent overwhelming external APIs.

        Args:
            documents: List of uploaded files
            client_id: Client UUID
            project_id: Project UUID
            organization_name: Organization name from assessment

        Returns:
            List of DocumentResult for each document
        """
        if not documents:
            return []

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOCUMENTS)

        async def process_with_semaphore(doc: UploadFile) -> DocumentResult:
            async with semaphore:
                return await self._process_single_document(
                    doc=doc,
                    client_id=client_id,
                    project_id=project_id,
                    organization_name=organization_name,
                )

        tasks = [process_with_semaphore(doc) for doc in documents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        doc_results: list[DocumentResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Document {documents[i].filename} failed: {result}")
                doc_results.append(
                    DocumentResult(
                        document_id=str(uuid.uuid4()),
                        filename=documents[i].filename or "unknown",
                        status="failed",
                    )
                )
            else:
                doc_results.append(result)

        return doc_results

    async def _process_single_document(
        self,
        doc: UploadFile,
        client_id: str,
        project_id: str,
        organization_name: str,
    ) -> DocumentResult:
        """
        Process a single document with LlamaExtract.

        Args:
            doc: Uploaded file
            client_id: Client UUID
            project_id: Project UUID
            organization_name: Organization name

        Returns:
            DocumentResult with processing status
        """
        doc_id = str(uuid.uuid4())
        filename = doc.filename or "unknown"
        temp_path = None
        extraction_result = None
        policy_enrichment = None

        try:
            # Save uploaded file to temp location
            content = await doc.read()
            suffix = os.path.splitext(filename)[1] if filename else ""
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name

            # Reset file position for potential downstream use
            await doc.seek(0)

            # Extract structured data from document
            extraction_result = await self._process_document_extraction(
                client_id=client_id,
                project_id=project_id,
                organization_name=organization_name,
                document_path=temp_path,
                filename=filename,
            )

            # Run policy analysis if extraction succeeded and produced text
            if extraction_result and extraction_result.get("status") == "success":
                extracted = extraction_result.get("extraction_result")
                extracted_text = getattr(extracted, "text", None) if extracted else None

                if extracted_text:
                    try:
                        policy_enrichment = await self._enrich_document_with_policies(
                            client_id=client_id,
                            project_id=project_id,
                            organization_name=organization_name,
                            filename=filename,
                            text=extracted_text,
                        )
                    except Exception as enrich_err:
                        logger.warning(
                            f"Policy enrichment failed for {filename}: {enrich_err}"
                        )

        except Exception as e:
            logger.error(f"Error processing document {filename}: {e}")
            extraction_result = {"status": "error", "error": str(e)}

        finally:
            # Clean up temp file
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

        # Determine status based on extraction result
        status = "pending"
        if extraction_result:
            if extraction_result.get("status") == "success":
                status = "processed"
            elif extraction_result.get("status") == "skipped":
                status = "pending"  # Will be processed by downstream agents
            elif extraction_result.get("status") == "error":
                status = "failed"

        result = DocumentResult(
            document_id=doc_id,
            filename=filename,
            status=status,
            extracted_text_length=(
                extraction_result.get("pgvector_chunks", 0) if extraction_result else 0
            ),
        )

        # Attach policy enrichment as extra metadata (not part of Pydantic model)
        # We use a private attribute so _build_response can collect it
        result._policy_enrichment = policy_enrichment  # type: ignore[attr-defined]

        return result

    async def _run_web_crawl(
        self,
        web_domain: str,
        client_id: str,
        project_id: str,
        force_refresh: bool = False,
    ) -> tuple[Optional[CrawlResult], bool]:
        """
        Run web crawler to extract business intelligence.

        Checks cache first unless force_refresh is True. Returns cached data
        if available and not expired.

        Isolated error handling - failures don't affect document processing.

        Args:
            web_domain: Domain to crawl
            client_id: Client UUID
            project_id: Project UUID
            force_refresh: If True, bypass cache and run fresh crawl

        Returns:
            Tuple of (CrawlResult if successful or None, from_cache boolean)
        """
        # Check cache first (unless force_refresh)
        if not force_refresh:
            cached = await self._get_cached_crawl_result(project_id, web_domain)
            if cached:
                return (cached, True)

        try:
            from app.services.web_crawler_agent import get_web_crawler_agent

            agent = await get_web_crawler_agent()
            crawl_request = CrawlRequest(
                web_domain=web_domain,
                client_id=client_id,
                project_id=project_id,
                max_pages=20,
            )

            # Use a well-known "system" UUID for internal operations
            # This avoids Supabase UUID validation errors while preserving audit context
            SYSTEM_USER_UUID = "00000000-0000-0000-0000-000000000000"
            result = await agent.crawl_domain(crawl_request, user_id=SYSTEM_USER_UUID)
            return (result, False)  # Fresh crawl, not from cache

        except Exception as e:
            logger.error(f"Web crawl failed for {web_domain}: {e}")
            # Return None instead of raising - allows document processing to succeed
            return (None, False)

    def _extract_result(
        self,
        results: list[Any],
        task_names: list[str],
        name: str,
        default: Any,
    ) -> Any:
        """
        Safely extract a result from the gathered results list.

        Args:
            results: List of results from asyncio.gather
            task_names: List of task names matching results order
            name: Name of task to extract
            default: Default value if not found or exception

        Returns:
            Result value or default
        """
        if name not in task_names:
            return default

        idx = task_names.index(name)
        if idx >= len(results):
            return default

        result = results[idx]
        if isinstance(result, Exception):
            logger.error(f"Task '{name}' failed with exception: {result}")
            return default

        return result

    def _build_summary(
        self,
        request: AssessmentRequest,
        doc_results: list[DocumentResult],
        web_crawl_result: Optional[CrawlResult],
        processing_time_ms: int,
    ) -> AssessmentSummary:
        """
        Build human-readable summary for frontend display.

        Args:
            request: Original assessment request
            doc_results: Results from document processing
            web_crawl_result: Result from web crawl (if run)
            processing_time_ms: Total processing time in milliseconds

        Returns:
            AssessmentSummary with headline, highlights, and next step guidance
        """
        highlights: list[str] = []

        # Document highlights
        if doc_results:
            processed = sum(1 for d in doc_results if d.status == "processed")
            pending = sum(1 for d in doc_results if d.status == "pending")
            failed = sum(1 for d in doc_results if d.status == "failed")

            if processed > 0:
                highlights.append(f"{processed} document(s) processed")
            if pending > 0:
                highlights.append(f"{pending} document(s) queued for processing")
            if failed > 0:
                highlights.append(f"{failed} document(s) failed")

        # Web crawl highlights
        if web_crawl_result and web_crawl_result.success:
            highlights.append(f"{web_crawl_result.pages_crawled} pages crawled")
            if web_crawl_result.digital_assets:
                highlights.append(
                    f"{len(web_crawl_result.digital_assets)} digital assets discovered"
                )
            if web_crawl_result.business_context:
                highlights.append("Business context extracted")
            if web_crawl_result.organization_info:
                highlights.append("Organization info extracted")

        # Determine next step based on what was processed
        if doc_results and any(d.status == "processed" for d in doc_results):
            next_step = "review_findings"
        elif doc_results:
            next_step = "upload_more_docs"
        else:
            next_step = "review_findings"

        return AssessmentSummary(
            headline=f"Assessment received for {request.organization_info.organization_name}",
            processing_time_ms=processing_time_ms,
            highlights=highlights,
            next_step=next_step,
            next_step_url=f"/clients/{request.client_id}/projects/{request.project_id}/findings",
        )

    def _build_response(
        self,
        assessment_id: str,
        request: AssessmentRequest,
        doc_results: list[DocumentResult],
        web_crawl_result: Optional[CrawlResult],
        from_cache: bool = False,
        org_context: Optional[OrganizationContextSummary] = None,
        processing_time_ms: int = 0,
    ) -> AssessmentResponse:
        """
        Build unified assessment response from all task results.

        Determines overall status based on success/failure of each component.

        Args:
            assessment_id: Unique assessment ID
            request: Original assessment request
            doc_results: Results from document processing
            web_crawl_result: Result from web crawl (if run)
            from_cache: Whether web crawl result was served from cache
            org_context: Organization context summary
            processing_time_ms: Total processing time in milliseconds

        Returns:
            AssessmentResponse with aggregated results
        """
        # Calculate failure counts
        doc_failures = sum(1 for d in doc_results if d.status == "failed")
        web_failed = (
            web_crawl_result is None or not web_crawl_result.success
            if request.organization_info.web_domain
            else False
        )

        # Determine overall status
        if len(doc_results) > 0 and doc_failures == len(doc_results) and web_failed:
            status = "failed"
        elif doc_failures > 0 or (request.organization_info.web_domain and web_failed):
            status = "partial"
        else:
            status = "received"

        # Build web crawl summary (only if domain was provided)
        web_crawl_summary: Optional[WebCrawlSummary] = None
        if request.organization_info.web_domain:
            if web_crawl_result and web_crawl_result.success:
                web_crawl_summary = WebCrawlSummary(
                    success=True,
                    pages_crawled=web_crawl_result.pages_crawled,
                    digital_assets_found=len(web_crawl_result.digital_assets),
                    business_context_extracted=web_crawl_result.business_context
                    is not None,
                    organization_info_extracted=web_crawl_result.organization_info
                    is not None,
                    confidence_score=web_crawl_result.confidence_score,
                    errors=web_crawl_result.errors,
                    from_cache=from_cache,
                    business_context=web_crawl_result.business_context.model_dump()
                    if web_crawl_result.business_context
                    else None,
                    digital_assets=[
                        a.model_dump() for a in web_crawl_result.digital_assets
                    ],
                    organization_info=web_crawl_result.organization_info.model_dump()
                    if web_crawl_result.organization_info
                    else None,
                )
            else:
                web_crawl_summary = WebCrawlSummary(
                    success=False,
                    pages_crawled=0,
                    digital_assets_found=0,
                    business_context_extracted=False,
                    organization_info_extracted=False,
                    confidence_score=0.0,
                    errors=["Web crawl failed or timed out"],
                    from_cache=False,
                )

        # Build summary for frontend display
        summary = self._build_summary(
            request=request,
            doc_results=doc_results,
            web_crawl_result=web_crawl_result,
            processing_time_ms=processing_time_ms,
        )

        # Ensure org_context exists (fallback if creation failed)
        if org_context is None:
            org_info = request.organization_info
            org_context = OrganizationContextSummary(
                created=False,
                organization_id=None,
                organization_name=org_info.organization_name,
                industry_type=org_info.industry_type.value
                if org_info.industry_type
                else "Unknown",
                industry_sector=None,
                department=org_info.department,
                scope_statement_preview=org_info.scope_statement_isms[:100]
                if org_info.scope_statement_isms
                else "",
                web_domain=org_info.web_domain,
                context_nodes=[],
                context_nodes_created=[],
            )

        # Collect policy enrichments from document results
        policy_enrichments = []
        for doc in doc_results:
            enrichment = getattr(doc, "_policy_enrichment", None)
            if enrichment:
                policy_enrichments.append(enrichment)

        # Build knowledge graph for React Flow visualization
        knowledge_graph = self._build_knowledge_graph(
            org_context=org_context,
            web_crawl_result=web_crawl_result,
            doc_results=doc_results,
            policy_enrichments=policy_enrichments if policy_enrichments else None,
        )

        return AssessmentResponse(
            assessment_id=assessment_id,
            project_id=request.project_id,
            documents_received=len(doc_results),
            status=status,
            documents=doc_results,
            web_crawl=web_crawl_summary,
            organization_context=org_context,
            knowledge_graph=knowledge_graph,
            summary=summary,
        )

    async def _process_document_extraction(
        self,
        client_id: str,
        project_id: str,
        organization_name: str,
        document_path: str,
        filename: str,
    ) -> dict:
        """
        Extract structured data from document and store in pgvector.

        Links all data to Company entity via client_id.

        Args:
            client_id: Client UUID (links to Company)
            project_id: Project UUID
            organization_name: Organization name from assessment form
            document_path: Path to temp file containing document
            filename: Original filename

        Returns:
            Dict with status and extraction details
        """
        from app.services.llama_extract_service import get_llama_extract_service
        from app.services.supabase_vector_service import get_supabase_vector_service

        extract_service = get_llama_extract_service()

        # Fall back to Python-native extraction if LlamaExtract not configured
        if not extract_service.is_available:
            logger.info("LlamaExtract unavailable, using fallback text extraction")
            return await self._process_document_fallback(
                client_id=client_id,
                project_id=project_id,
                organization_name=organization_name,
                document_path=document_path,
                filename=filename,
            )

        try:
            # Extract with schema inference
            extraction_result = await extract_service.infer_and_extract(document_path)
            extracted_data = extraction_result["data"]

            # Store in pgvector for semantic search (linked to Company via client_id)
            vector_svc = get_supabase_vector_service()

            # Flatten extracted data to searchable text fields
            searchable_fields = self._flatten_for_search(
                extracted_data
                if isinstance(extracted_data, dict)
                else extracted_data.model_dump()
            )
            chunk_ids = await vector_svc.upsert_extracted_data(
                client_id=client_id,
                project_id=project_id,
                document_id=filename,
                extracted_fields=searchable_fields,
                doc_type="llama_extraction",
            )

            logger.info(
                f"Extracted {filename}: pgvector_chunks={len(chunk_ids)}"
            )

            return {
                "status": "success",
                "pgvector_chunks": len(chunk_ids),
                "schema_type": extraction_result["schema"],
            }

        except Exception as e:
            logger.error(f"Extraction failed for {filename}: {e}")
            return {"status": "error", "error": str(e)}

    async def _process_document_fallback(
        self,
        client_id: str,
        project_id: str,
        organization_name: str,
        document_path: str,
        filename: str,
    ) -> dict:
        """
        Fallback document extraction using Python-native libraries.

        Used when LlamaExtract (LLAMA_CLOUD_API_KEY) is not configured.
        Extracts text via pypdf/python-docx/openpyxl, stores in pgvector.

        Args:
            client_id: Client UUID
            project_id: Project UUID
            organization_name: Organization name from assessment form
            document_path: Path to temp file on disk
            filename: Original filename

        Returns:
            Dict with status and extraction details
        """
        from app.services.document_text_extractor import DocumentTextExtractor
        from app.services.supabase_vector_service import get_supabase_vector_service

        try:
            extractor = DocumentTextExtractor()
            extraction = await extractor.extract_text(document_path, filename)

            if not extraction.text or len(extraction.text.strip()) < 10:
                logger.warning(f"Fallback extraction produced no text for {filename}")
                return {"status": "error", "error": "No text extracted from document"}

            # Store text chunks in pgvector for semantic search
            vector_svc = get_supabase_vector_service()

            # Split text into searchable chunks
            searchable_fields = self._split_text_to_fields(extraction.text, filename)
            chunk_ids = await vector_svc.upsert_extracted_data(
                client_id=client_id,
                project_id=project_id,
                document_id=filename,
                extracted_fields=searchable_fields,
                doc_type="fallback_extraction",
            )

            logger.info(
                f"Fallback extracted {filename}: "
                f"pgvector_chunks={len(chunk_ids)}, words={extraction.word_count}"
            )

            return {
                "status": "success",
                "pgvector_chunks": len(chunk_ids),
                "schema_type": "fallback",
                "extraction_result": extraction,
            }

        except Exception as e:
            logger.error(f"Fallback extraction failed for {filename}: {e}")
            return {"status": "error", "error": str(e)}

    async def _enrich_document_with_policies(
        self,
        client_id: str,
        project_id: str,
        organization_name: str,
        filename: str,
        text: str,
    ) -> dict:
        """
        Analyze document text for policy content.

        Uses Claude to classify documents as policies and map to controls.
        Returns analysis results (no longer stores in Neo4j).

        Args:
            client_id: Client UUID
            project_id: Project UUID
            organization_name: Organization name
            filename: Original filename
            text: Extracted document text

        Returns:
            Dict with enrichment status and details
        """
        from app.services.document_analyzer import DocumentAnalyzer

        try:
            analyzer = DocumentAnalyzer()
            if not analyzer.is_available:
                return {"policy_analysis": "skipped", "reason": "no_anthropic_key"}

            analysis = await analyzer.analyze_document(
                text=text,
                filename=filename,
                org_context=f"Organization: {organization_name}",
            )

            if not analysis.is_policy:
                return {
                    "policy_analysis": "not_policy",
                    "confidence": analysis.confidence,
                }

            # Collect control mappings from Claude analysis
            controls_mapped = []
            for ctrl in analysis.controls_addressed:
                controls_mapped.append(
                    {
                        "framework": ctrl.framework,
                        "identifier": ctrl.identifier,
                        "title": ctrl.title,
                        "compliance_level": ctrl.compliance_level,
                        "evidence": ctrl.evidence,
                        "gap": ctrl.gap,
                    }
                )

            logger.info(
                f"Policy enrichment for {filename}: type={analysis.policy_type}, "
                f"controls_mapped={len(controls_mapped)}"
            )

            return {
                "policy_analysis": "success",
                "policy_type": analysis.policy_type,
                "controls_mapped": len(controls_mapped),
                "control_details": controls_mapped,
                "confidence": analysis.confidence,
            }

        except Exception as e:
            logger.error(f"Policy enrichment failed for {filename}: {e}")
            return {"policy_analysis": "error", "error": str(e)}

    def _split_text_to_fields(
        self, text: str, filename: str, chunk_size: int = 1500
    ) -> dict[str, str]:
        """
        Split document text into chunks suitable for embedding.

        Args:
            text: Full document text
            filename: Source filename
            chunk_size: Target characters per chunk

        Returns:
            Dict of field_name -> text_value for vector storage
        """
        fields = {}
        words = text.split()

        # Build chunks of approximately chunk_size characters
        current_chunk = []
        current_length = 0
        chunk_index = 0

        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1

            if current_length >= chunk_size:
                fields[f"chunk_{chunk_index}"] = " ".join(current_chunk)
                current_chunk = []
                current_length = 0
                chunk_index += 1

        # Don't forget the last chunk
        if current_chunk:
            fields[f"chunk_{chunk_index}"] = " ".join(current_chunk)

        return fields

    def _flatten_for_search(self, data: dict, prefix: str = "") -> dict[str, str]:
        """
        Flatten nested dict to field_name -> text pairs for embedding.

        Args:
            data: Nested dictionary to flatten
            prefix: Prefix for nested keys

        Returns:
            Dict of field_name -> text_value for fields with substantial text
        """
        result = {}

        for key, value in data.items():
            field_name = f"{prefix}{key}" if prefix else key

            if isinstance(value, str) and len(value) > 10:
                result[field_name] = value
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, str) and len(item) > 10:
                        result[f"{field_name}_{i}"] = item
                    elif isinstance(item, dict):
                        result.update(
                            self._flatten_for_search(item, f"{field_name}_{i}_")
                        )
            elif isinstance(value, dict):
                result.update(self._flatten_for_search(value, f"{field_name}_"))

        return result

    async def get_assessment_status(self, assessment_id: str) -> dict | None:
        """
        Get current status of an assessment.

        Args:
            assessment_id: The assessment UUID

        Returns:
            Assessment state dict or None if not found
        """
        return self.active_assessments.get(assessment_id)


def get_orchestrator() -> AssessmentOrchestrator:
    """Get singleton orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AssessmentOrchestrator()
    return _orchestrator


def reset_orchestrator() -> None:
    """Reset orchestrator for testing."""
    global _orchestrator
    _orchestrator = None
