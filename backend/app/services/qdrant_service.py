"""Qdrant service for vector search operations."""

import logging
import time
import uuid
from typing import Optional

from qdrant_client import AsyncQdrantClient, models
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.models.search import (
    DocumentChunk,
    IndexStats,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

COLLECTION_NAME = "pga_documents"


class QdrantService:
    """Service for vector search using Qdrant."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            check_compatibility=False,  # Allow version mismatch
        )
        self._embedding_service = get_embedding_service()
        self._dimensions = settings.embedding_dimensions
        self._collection_initialized = False

    async def initialize(self) -> None:
        """Initialize Qdrant collection with proper schema."""
        if self._collection_initialized:
            return

        try:
            collections = await self._client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if COLLECTION_NAME not in collection_names:
                logger.info(f"Creating Qdrant collection: {COLLECTION_NAME}")
                await self._client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=models.VectorParams(
                        size=self._dimensions,
                        distance=models.Distance.COSINE,
                    ),
                )

                # Create payload indexes for filtering
                await self._create_payload_indexes()

            # Diagnostic log for search attribute issue
            has_search = hasattr(self._client, 'search')
            client_type = type(self._client).__name__
            logger.info(f"Qdrant client type: {client_type}, has 'search' attribute: {has_search}")
            if not has_search:
                logger.warning(f"Available attributes on {client_type}: {dir(self._client)}")

            self._collection_initialized = True
            logger.info("Qdrant collection initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {e}")
            raise

    async def _create_payload_indexes(self) -> None:
        """Create indexes on payload fields for efficient filtering."""
        index_fields = [
            ("project_id", models.PayloadSchemaType.KEYWORD),
            ("client_id", models.PayloadSchemaType.KEYWORD),
            ("document_id", models.PayloadSchemaType.KEYWORD),
            ("framework", models.PayloadSchemaType.KEYWORD),
            ("doc_type", models.PayloadSchemaType.KEYWORD),
        ]

        for field_name, field_type in index_fields:
            try:
                await self._client.create_payload_index(
                    collection_name=COLLECTION_NAME,
                    field_name=field_name,
                    field_schema=field_type,
                )
                logger.debug(f"Created index on {field_name}")
            except Exception as e:
                # Index may already exist
                logger.debug(f"Index creation skipped for {field_name}: {e}")

    async def close(self) -> None:
        """Close the Qdrant client connection."""
        await self._client.close()
        logger.info("Qdrant connection closed")

    async def health_check(self) -> dict:
        """Check Qdrant connection health."""
        try:
            info = await self._client.get_collection(COLLECTION_NAME)
            return {
                "status": "healthy",
                "collection": COLLECTION_NAME,
                "points_count": info.points_count,
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def upsert_chunk(self, chunk: DocumentChunk, embedding: list[float]) -> str:
        """
        Insert or update a single document chunk with its embedding.

        Returns the chunk ID.
        """
        await self.initialize()

        chunk_id = chunk.id or str(uuid.uuid4())

        payload = {
            "document_id": chunk.document_id,
            "project_id": chunk.project_id,
            "client_id": chunk.client_id,
            "chunk_index": chunk.chunk_index,
            "text": chunk.text,
            "token_count": chunk.token_count,
            "doc_type": chunk.doc_type,
            "framework": chunk.framework.value if chunk.framework else None,
            "control_ids": chunk.control_ids,
            "filename": chunk.filename,
            "start_char": chunk.start_char,
            "end_char": chunk.end_char,
        }

        await self._client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=chunk_id,
                    vector=embedding,
                    payload=payload,
                )
            ],
        )

        return chunk_id

    async def upsert_chunks_batch(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> list[str]:
        """
        Batch insert/update multiple chunks with embeddings.

        Returns list of chunk IDs.
        """
        await self.initialize()

        if len(chunks) != len(embeddings):
            raise ValueError("Chunks and embeddings must have same length")

        points = []
        chunk_ids = []

        for chunk, embedding in zip(chunks, embeddings):
            chunk_id = chunk.id or str(uuid.uuid4())
            chunk_ids.append(chunk_id)

            payload = {
                "document_id": chunk.document_id,
                "project_id": chunk.project_id,
                "client_id": chunk.client_id,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "token_count": chunk.token_count,
                "doc_type": chunk.doc_type,
                "framework": chunk.framework.value if chunk.framework else None,
                "control_ids": chunk.control_ids,
                "filename": chunk.filename,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
            }

            points.append(
                models.PointStruct(
                    id=chunk_id,
                    vector=embedding,
                    payload=payload,
                )
            )

        # Batch upsert in groups of 100
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            await self._client.upsert(
                collection_name=COLLECTION_NAME,
                points=batch,
            )

        logger.info(f"Upserted {len(chunks)} chunks to Qdrant")
        return chunk_ids

    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Perform semantic search with filters.

        Returns SearchResponse with matching chunks.
        """
        await self.initialize()

        # Generate query embedding
        embed_start = time.time()
        query_embedding = await self._embedding_service.embed_text(request.query)
        embed_time = (time.time() - embed_start) * 1000

        # Build filter conditions
        must_conditions = [
            models.FieldCondition(
                key="project_id",
                match=models.MatchValue(value=request.project_id),
            )
        ]

        if request.framework:
            must_conditions.append(
                models.FieldCondition(
                    key="framework",
                    match=models.MatchValue(value=request.framework.value),
                )
            )

        if request.doc_type:
            must_conditions.append(
                models.FieldCondition(
                    key="doc_type",
                    match=models.MatchValue(value=request.doc_type),
                )
            )

        if request.document_ids:
            must_conditions.append(
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchAny(any=request.document_ids),
                )
            )

        if request.control_ids:
            # Match any of the control IDs
            must_conditions.append(
                models.FieldCondition(
                    key="control_ids",
                    match=models.MatchAny(any=request.control_ids),
                )
            )

        search_filter = models.Filter(must=must_conditions)

        # Execute search
        search_start = time.time()
        try:
            results = await self._client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=request.limit,
                offset=request.offset,
                score_threshold=request.score_threshold,
                with_payload=request.include_metadata,
            )
        except AttributeError:
            # Fallback for some versions where it might be slightly different or for debugging
            logger.error(f"AsyncQdrantClient search attribute error. Client type: {type(self._client)}")
            # Try query_points as fallback if search is missing in some async versions
            if hasattr(self._client, 'query_points'):
                results = await self._client.query_points(
                    collection_name=COLLECTION_NAME,
                    prefetch=[
                        models.Prefetch(
                            query=query_embedding, # Use query instead of vector
                            limit=request.limit,
                            filter=search_filter,
                        )
                    ]
                )
                results = results.points
            else:
                raise
        search_time = (time.time() - search_start) * 1000

        # Convert to response model
        search_results = []
        for hit in results:
            payload = hit.payload or {}
            search_results.append(
                SearchResult(
                    chunk_id=str(hit.id),
                    document_id=payload.get("document_id", ""),
                    score=hit.score,
                    text=payload.get("text", ""),
                    filename=payload.get("filename"),
                    doc_type=payload.get("doc_type"),
                    control_ids=payload.get("control_ids", []),
                    chunk_index=payload.get("chunk_index", 0),
                    highlight=self._create_highlight(
                        payload.get("text", ""), request.query
                    ),
                )
            )

        # Build filters applied dict
        filters_applied = {"project_id": request.project_id}
        if request.framework:
            filters_applied["framework"] = request.framework.value
        if request.doc_type:
            filters_applied["doc_type"] = request.doc_type
        if request.document_ids:
            filters_applied["document_ids"] = request.document_ids
        if request.control_ids:
            filters_applied["control_ids"] = request.control_ids

        return SearchResponse(
            query=request.query,
            results=search_results,
            total_count=len(search_results),  # Would need scroll for true total
            returned_count=len(search_results),
            search_time_ms=search_time,
            embedding_time_ms=embed_time,
            filters_applied=filters_applied,
        )

    def _create_highlight(self, text: str, query: str, context_chars: int = 100) -> str:
        """Create a highlighted snippet around query terms."""
        text_lower = text.lower()
        query_lower = query.lower()

        # Find query terms in text
        query_words = query_lower.split()
        best_pos = -1
        for word in query_words:
            pos = text_lower.find(word)
            if pos != -1:
                best_pos = pos
                break

        if best_pos == -1:
            # Return start of text if no match found
            return (
                text[: context_chars * 2] + "..."
                if len(text) > context_chars * 2
                else text
            )

        # Extract context around match
        start = max(0, best_pos - context_chars)
        end = min(len(text), best_pos + context_chars)

        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet

    async def delete_document_chunks(self, document_id: str) -> int:
        """
        Delete all chunks for a document.

        Returns count of deleted chunks.
        """
        await self.initialize()

        # Count before deletion
        count_result = await self._client.count(
            collection_name=COLLECTION_NAME,
            count_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id),
                    )
                ]
            ),
        )
        count = count_result.count

        if count > 0:
            await self._client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
            )
            logger.info(f"Deleted {count} chunks for document {document_id}")

        return count

    async def get_index_stats(self, project_id: str) -> IndexStats:
        """Get index statistics for a project."""
        await self.initialize()

        # Count total chunks for project
        count_result = await self._client.count(
            collection_name=COLLECTION_NAME,
            count_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="project_id",
                        match=models.MatchValue(value=project_id),
                    )
                ]
            ),
        )

        # Get unique documents (scroll through all and count unique)
        # For now, return basic stats - would need aggregation for breakdown
        return IndexStats(
            project_id=project_id,
            total_chunks=count_result.count,
            total_documents=0,  # Would need aggregation
            collection_name=COLLECTION_NAME,
            dimensions=self._dimensions,
            chunks_by_doc_type={},
            chunks_by_framework={},
        )

    # --- Extracted Data Operations ---

    async def upsert_extracted_data(
        self,
        client_id: str,
        project_id: str,
        document_id: str,
        extracted_fields: dict[str, str],
        doc_type: str = "llama_extraction",
    ) -> list[str]:
        """
        Embed and store extracted field values for semantic search.

        Each field becomes a searchable chunk linked to client/company.

        Args:
            client_id: Client UUID (links to Company entity)
            project_id: Project UUID
            document_id: Document identifier
            extracted_fields: Dict of field_name -> text_value
            doc_type: Document type tag (default: llama_extraction)

        Returns:
            List of chunk IDs created
        """
        await self.initialize()

        chunks = []
        texts = []

        for field_name, field_value in extracted_fields.items():
            if not field_value or not isinstance(field_value, str):
                continue
            if len(field_value.strip()) < 10:
                continue

            chunk_id = f"{document_id}_{field_name}"
            chunks.append(
                {
                    "id": chunk_id,
                    "client_id": client_id,
                    "project_id": project_id,
                    "document_id": document_id,
                    "field_name": field_name,
                    "text": field_value,
                    "doc_type": doc_type,
                }
            )
            texts.append(field_value)

        if not chunks:
            return []

        # Generate embeddings
        embeddings = await self._embedding_service.embed_texts(texts)

        # Build points
        points = []
        for chunk, embedding in zip(chunks, embeddings):
            points.append(
                models.PointStruct(
                    id=chunk["id"],
                    vector=embedding,
                    payload=chunk,
                )
            )

        # Upsert to Qdrant
        await self._client.upsert(collection_name=COLLECTION_NAME, points=points)

        logger.info(
            f"Upserted {len(chunks)} extracted chunks for document {document_id}"
        )
        return [c["id"] for c in chunks]

    async def search_company_extractions(
        self,
        client_id: str,
        query: str,
        limit: int = 10,
    ) -> list[dict]:
        """
        Search extracted data for a specific company.

        Args:
            client_id: Client UUID to filter by
            query: Search query text
            limit: Maximum results to return

        Returns:
            List of matching chunks with id, score, and payload
        """
        await self.initialize()

        query_embedding = await self._embedding_service.embed_text(query)

        try:
            results = await self._client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_embedding,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="client_id",
                            match=models.MatchValue(value=client_id),
                        ),
                        models.FieldCondition(
                            key="doc_type",
                            match=models.MatchValue(value="llama_extraction"),
                        ),
                    ]
                ),
                limit=limit,
            )
        except AttributeError:
            if hasattr(self._client, 'query_points'):
                results = await self._client.query_points(
                    collection_name=COLLECTION_NAME,
                    prefetch=[
                        models.Prefetch(
                            query=query_embedding, # Use query instead of vector
                            limit=limit,
                            filter=models.Filter(
                                must=[
                                    models.FieldCondition(
                                        key="client_id",
                                        match=models.MatchValue(value=client_id),
                                    ),
                                    models.FieldCondition(
                                        key="doc_type",
                                        match=models.MatchValue(value="llama_extraction"),
                                    ),
                                ]
                            ),
                        )
                    ]
                ).points
            else:
                raise

        return [{"id": str(r.id), "score": r.score, **r.payload} for r in results]


# Singleton pattern
_qdrant_service: Optional[QdrantService] = None


def get_qdrant_service() -> QdrantService:
    """Get cached Qdrant service instance."""
    global _qdrant_service
    if _qdrant_service is None:
        _qdrant_service = QdrantService()
    return _qdrant_service


def reset_qdrant_service() -> None:
    """Reset service for testing."""
    global _qdrant_service
    _qdrant_service = None
