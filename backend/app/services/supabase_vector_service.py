"""Supabase pgvector service — drop-in replacement for QdrantService.

Uses the ``document_chunks`` table + ``match_document_chunks`` /
``match_client_extractions`` RPC functions created by migration 015.
"""

import logging
import uuid
from typing import Optional

from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class SupabaseVectorService:
    """Vector search backed by Supabase pgvector."""

    def __init__(self) -> None:
        self._embedding_service = get_embedding_service()

    async def _get_client(self):
        """Lazy-load async Supabase client."""
        from app.db.supabase import get_async_supabase_client_async

        return await get_async_supabase_client_async()

    async def upsert_extracted_data(
        self,
        client_id: str,
        project_id: str,
        document_id: str,
        extracted_fields: dict[str, str],
        doc_type: str = "llama_extraction",
    ) -> list[str]:
        """Embed and store extracted field values for semantic search.

        Each field becomes a searchable chunk in ``document_chunks``.

        Args:
            client_id: Client UUID
            project_id: Project UUID
            document_id: Document identifier
            extracted_fields: Dict of field_name -> text_value
            doc_type: Document type tag

        Returns:
            List of chunk UUIDs created.
        """
        rows: list[dict] = []
        texts: list[str] = []

        for field_name, field_value in extracted_fields.items():
            if not field_value or not isinstance(field_value, str):
                continue
            if len(field_value.strip()) < 10:
                continue

            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "client_id": client_id,
                    "project_id": project_id,
                    "document_id": document_id,
                    "field_name": field_name,
                    "text": field_value,
                    "doc_type": doc_type,
                    "chunk_index": len(rows),
                    "token_count": self._embedding_service.count_tokens(field_value),
                }
            )
            texts.append(field_value)

        if not rows:
            return []

        # Generate embeddings in batch
        embeddings = await self._embedding_service.embed_texts(texts)

        # Attach embedding vectors
        for row, emb in zip(rows, embeddings):
            row["embedding"] = emb

        # Bulk insert into document_chunks
        sb = await self._get_client()
        await sb.table("document_chunks").insert(rows).execute()

        chunk_ids = [r["id"] for r in rows]
        logger.info(
            f"Upserted {len(chunk_ids)} chunks for document {document_id} via pgvector"
        )
        return chunk_ids

    async def search_document_chunks(
        self,
        project_id: str,
        query: str,
        limit: int = 10,
        threshold: float = 0.3,
        framework: Optional[str] = None,
        doc_type: Optional[str] = None,
        document_ids: Optional[list[str]] = None,
    ) -> list[dict]:
        """Semantic search via ``match_document_chunks`` RPC.

        Args:
            project_id: Project UUID to scope search
            query: Natural-language search query
            limit: Max results
            threshold: Minimum cosine similarity
            framework: Optional framework filter
            doc_type: Optional doc_type filter
            document_ids: Optional list of document_id values to restrict search

        Returns:
            List of matching chunk dicts with ``similarity`` score.
        """
        query_embedding = await self._embedding_service.embed_text(query)

        sb = await self._get_client()
        result = await sb.rpc(
            "match_document_chunks",
            {
                "query_embedding": query_embedding,
                "match_project_id": project_id,
                "match_threshold": threshold,
                "match_count": limit,
                "filter_framework": framework,
                "filter_doc_type": doc_type,
                "filter_document_ids": document_ids,
            },
        ).execute()

        return result.data or []

    async def search_client_extractions(
        self,
        client_id: str,
        query: str,
        limit: int = 10,
    ) -> list[dict]:
        """Search extracted data for a specific client.

        Calls ``match_client_extractions`` RPC (replaces
        ``QdrantService.search_company_extractions``).

        Args:
            client_id: Client UUID
            query: Search query text
            limit: Max results

        Returns:
            List of matching chunk dicts.
        """
        query_embedding = await self._embedding_service.embed_text(query)

        sb = await self._get_client()
        result = await sb.rpc(
            "match_client_extractions",
            {
                "query_embedding": query_embedding,
                "match_client_id": client_id,
                "match_count": limit,
            },
        ).execute()

        return result.data or []

    async def get_index_stats(self, project_id: str) -> dict:
        """Return basic stats for a project's document chunks."""
        sb = await self._get_client()
        result = (
            await sb.table("document_chunks")
            .select("id", count="exact")
            .eq("project_id", project_id)
            .execute()
        )
        return {
            "project_id": project_id,
            "total_chunks": result.count or 0,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_service: Optional[SupabaseVectorService] = None


def get_supabase_vector_service() -> SupabaseVectorService:
    """Get cached SupabaseVectorService instance."""
    global _service
    if _service is None:
        _service = SupabaseVectorService()
    return _service


def reset_supabase_vector_service() -> None:
    """Reset for testing."""
    global _service
    _service = None
