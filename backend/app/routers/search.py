"""Semantic search API router."""

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_user
from app.models.search import IndexStats, SearchRequest, SearchResponse
from app.services.qdrant_service import get_qdrant_service

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    current_user: dict = Depends(get_current_user),
) -> SearchResponse:
    """
    Perform semantic search across indexed documents.

    Searches document chunks using vector similarity with optional filters:
    - framework: Filter by compliance framework (iso_27001, bnm_rmit)
    - doc_type: Filter by document type
    - control_ids: Filter by related control identifiers
    - document_ids: Filter by specific documents

    Returns ranked results with similarity scores and highlighted snippets.
    """
    qdrant = get_qdrant_service()

    try:
        return await qdrant.search(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/stats/{project_id}", response_model=IndexStats)
async def get_index_stats(
    project_id: str,
    current_user: dict = Depends(get_current_user),
) -> IndexStats:
    """
    Get index statistics for a project.

    Returns counts of indexed chunks and documents
    with breakdown by document type and framework.
    """
    qdrant = get_qdrant_service()
    return await qdrant.get_index_stats(project_id)


@router.delete("/index/{document_id}")
async def delete_document_index(
    document_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Remove all indexed chunks for a document.

    Use this when a document is deleted or needs to be re-indexed.
    Returns the count of deleted chunks.
    """
    qdrant = get_qdrant_service()
    count = await qdrant.delete_document_chunks(document_id)

    return {
        "document_id": document_id,
        "chunks_deleted": count,
        "status": "deleted" if count > 0 else "not_found",
    }


@router.get("/health")
async def search_health_check(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Check health of the search service.

    Returns Qdrant connection status and collection info.
    """
    qdrant = get_qdrant_service()
    return await qdrant.health_check()
