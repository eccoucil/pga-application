"""Embedding service using OpenAI text-embedding-3-small."""

import logging
from typing import Optional

import tiktoken
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

logger = logging.getLogger(__name__)

# Chunking configuration
DEFAULT_CHUNK_SIZE = 512  # tokens
DEFAULT_CHUNK_OVERLAP = 50  # tokens
MAX_BATCH_SIZE = 2048  # OpenAI batch limit


class EmbeddingService:
    """Service for generating text embeddings using OpenAI."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not configured - embeddings disabled")
            self._client: Optional[AsyncOpenAI] = None
        else:
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)

        self._model = settings.embedding_model
        self._dimensions = settings.embedding_dimensions
        self._encoding = tiktoken.encoding_for_model("gpt-4")  # Compatible with ada

    @property
    def is_available(self) -> bool:
        """Check if embedding service is configured and available."""
        return self._client is not None

    @property
    def dimensions(self) -> int:
        """Get embedding dimensions."""
        return self._dimensions

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self._encoding.encode(text))

    def chunk_text(
        self,
        text: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> list[dict]:
        """
        Split text into overlapping chunks based on token count.

        Returns list of dicts with:
        - text: chunk content
        - start_char: start position in original
        - end_char: end position in original
        - token_count: tokens in chunk
        """
        if not text.strip():
            return []

        tokens = self._encoding.encode(text)
        chunks = []
        start_token = 0

        while start_token < len(tokens):
            end_token = min(start_token + chunk_size, len(tokens))
            chunk_tokens = tokens[start_token:end_token]
            chunk_text = self._encoding.decode(chunk_tokens)

            # Calculate character positions (approximate)
            # We need to find where this chunk starts/ends in original text
            prefix_tokens = tokens[:start_token]
            prefix_text = self._encoding.decode(prefix_tokens) if prefix_tokens else ""
            start_char = len(prefix_text)
            end_char = start_char + len(chunk_text)

            chunks.append(
                {
                    "text": chunk_text,
                    "start_char": start_char,
                    "end_char": end_char,
                    "token_count": len(chunk_tokens),
                }
            )

            # Move to next chunk with overlap
            start_token = end_token - overlap
            if start_token >= len(tokens):
                break

        logger.debug(f"Split text into {len(chunks)} chunks")
        return chunks

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Returns embedding vector of configured dimensions.
        Raises ValueError if service not configured.
        """
        if not self._client:
            raise ValueError("OpenAI API key not configured")

        text = text.replace("\n", " ").strip()
        if not text:
            raise ValueError("Cannot embed empty text")

        response = await self._client.embeddings.create(
            model=self._model,
            input=text,
            dimensions=self._dimensions,
        )

        return response.data[0].embedding

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts (max 2048)

        Returns:
            List of embedding vectors
        """
        if not self._client:
            raise ValueError("OpenAI API key not configured")

        if len(texts) > MAX_BATCH_SIZE:
            raise ValueError(f"Batch size exceeds maximum of {MAX_BATCH_SIZE}")

        # Clean and validate texts
        cleaned = [t.replace("\n", " ").strip() for t in texts]
        if not all(cleaned):
            raise ValueError("Cannot embed empty texts")

        response = await self._client.embeddings.create(
            model=self._model,
            input=cleaned,
            dimensions=self._dimensions,
        )

        # Sort by index to ensure correct ordering
        sorted_embeddings = sorted(response.data, key=lambda x: x.index)
        return [e.embedding for e in sorted_embeddings]

    async def embed_chunks(
        self, text: str, chunk_size: int = DEFAULT_CHUNK_SIZE
    ) -> list[tuple[dict, list[float]]]:
        """
        Chunk text and generate embeddings for each chunk.

        Returns list of (chunk_info, embedding) tuples.
        """
        chunks = self.chunk_text(text, chunk_size)
        if not chunks:
            return []

        texts = [c["text"] for c in chunks]

        # Batch in groups of MAX_BATCH_SIZE
        all_embeddings = []
        for i in range(0, len(texts), MAX_BATCH_SIZE):
            batch = texts[i : i + MAX_BATCH_SIZE]
            embeddings = await self.embed_texts(batch)
            all_embeddings.extend(embeddings)

        return list(zip(chunks, all_embeddings))


# Singleton pattern
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get cached embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def reset_embedding_service() -> None:
    """Reset service for testing."""
    global _embedding_service
    _embedding_service = None
