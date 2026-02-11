"""Search models for Qdrant semantic search."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.knowledge_graph import FrameworkType


class DocumentChunk(BaseModel):
    """A chunk of text from a document for embedding."""

    id: Optional[str] = Field(None, description="Chunk UUID")
    document_id: str = Field(..., description="Parent document UUID")
    project_id: str = Field(..., description="Project UUID for multi-tenancy")
    client_id: str = Field(..., description="Client UUID for multi-tenancy")
    chunk_index: int = Field(..., description="Index of this chunk in document")
    text: str = Field(..., description="Chunk text content")
    token_count: int = Field(0, description="Number of tokens in chunk")

    # Metadata for filtering
    doc_type: Optional[str] = Field(None, description="Document type")
    framework: Optional[FrameworkType] = Field(None, description="Related framework")
    control_ids: list[str] = Field(
        default_factory=list, description="Related control IDs"
    )
    filename: Optional[str] = Field(None, description="Source filename")

    # Positional metadata
    start_char: int = Field(0, description="Start character position in original")
    end_char: int = Field(0, description="End character position in original")

    created_at: datetime = Field(default_factory=datetime.utcnow)


class SearchRequest(BaseModel):
    """Semantic search request with filters."""

    query: str = Field(..., min_length=3, description="Search query text")
    project_id: str = Field(..., description="Project UUID to search within")

    # Filters
    framework: Optional[FrameworkType] = Field(None, description="Filter by framework")
    doc_type: Optional[str] = Field(None, description="Filter by document type")
    control_ids: Optional[list[str]] = Field(
        None, description="Filter by related controls"
    )
    document_ids: Optional[list[str]] = Field(
        None, description="Filter by specific documents"
    )

    # Pagination
    limit: int = Field(10, ge=1, le=100, description="Number of results")
    offset: int = Field(0, ge=0, description="Offset for pagination")

    # Search options
    score_threshold: float = Field(
        0.7, ge=0.0, le=1.0, description="Minimum similarity score"
    )
    include_metadata: bool = Field(True, description="Include metadata in results")


class SearchResult(BaseModel):
    """Single search result with relevance info."""

    chunk_id: str = Field(..., description="Chunk UUID")
    document_id: str = Field(..., description="Parent document UUID")
    score: float = Field(..., description="Similarity score (0-1)")
    text: str = Field(..., description="Matching chunk text")

    # Optional metadata
    filename: Optional[str] = Field(None, description="Source filename")
    doc_type: Optional[str] = Field(None, description="Document type")
    control_ids: list[str] = Field(default_factory=list, description="Related controls")
    chunk_index: int = Field(0, description="Position in document")

    # Highlight (context around match)
    highlight: Optional[str] = Field(
        None, description="Highlighted snippet around match"
    )


class SearchResponse(BaseModel):
    """Full search response with results and metadata."""

    query: str = Field(..., description="Original query")
    results: list[SearchResult] = Field(
        default_factory=list, description="Matching results"
    )
    total_count: int = Field(0, description="Total matching chunks")
    returned_count: int = Field(0, description="Number of results returned")

    # Timing
    search_time_ms: float = Field(0.0, description="Search execution time in ms")
    embedding_time_ms: float = Field(0.0, description="Embedding generation time in ms")

    # Filters applied
    filters_applied: dict = Field(
        default_factory=dict, description="Filters that were applied"
    )


class IndexStats(BaseModel):
    """Statistics about the Qdrant index for a project."""

    project_id: str = Field(..., description="Project UUID")
    total_chunks: int = Field(0, description="Total chunks indexed")
    total_documents: int = Field(0, description="Unique documents indexed")
    collection_name: str = Field(..., description="Qdrant collection name")
    dimensions: int = Field(1536, description="Embedding dimensions")

    # Breakdown by type
    chunks_by_doc_type: dict[str, int] = Field(
        default_factory=dict, description="Chunks per document type"
    )
    chunks_by_framework: dict[str, int] = Field(
        default_factory=dict, description="Chunks per framework"
    )
