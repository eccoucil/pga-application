"""LlamaExtract service for structured data extraction from documents."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, Optional, Type, TypeVar

from pydantic import BaseModel

from app.config import get_settings
from app.models.extraction_schemas import GenericDocumentExtraction

if TYPE_CHECKING:
    from llama_cloud_services import LlamaExtract

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class LlamaExtractService:
    """Service for structured data extraction using LlamaExtract."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.llama_cloud_api_key
        self._client: Optional[LlamaExtract] = None
        self._agents: dict[str, Any] = {}

    @property
    def is_available(self) -> bool:
        """Check if LlamaExtract is configured."""
        return self._api_key is not None

    def _get_client(self) -> LlamaExtract:
        """Get or create LlamaExtract client."""
        if self._client is None:
            if not self._api_key:
                raise ValueError("LLAMA_CLOUD_API_KEY not configured")

            # Set API key in environment for llama-cloud-services
            os.environ["LLAMA_CLOUD_API_KEY"] = self._api_key

            from llama_cloud_services import LlamaExtract

            self._client = LlamaExtract()

        return self._client

    def get_or_create_agent(self, name: str, schema: Type[T]) -> object:
        """Get or create an extraction agent for a schema."""
        if name not in self._agents:
            client = self._get_client()
            self._agents[name] = client.create_agent(name=name, data_schema=schema)
        return self._agents[name]

    async def infer_and_extract(self, file_path: str) -> dict:
        """
        Infer schema from document and extract structured data.

        Uses GenericDocumentExtraction as fallback if inference fails.

        Args:
            file_path: Path to the document file

        Returns:
            Dict with 'schema' (inferred/generic) and 'data' (extracted data)
        """
        client = self._get_client()

        try:
            # Try to infer schema from document
            inferred_schema = client.infer_schema(
                f"inferred-{os.path.basename(file_path)}", [file_path]
            )
            agent = client.create_agent(
                name=f"dynamic-{os.path.basename(file_path)}",
                data_schema=inferred_schema,
            )
            result = agent.extract(file_path)
            return {"schema": "inferred", "data": result.data}

        except Exception as e:
            logger.warning(f"Schema inference failed, using generic: {e}")

            # Fallback to generic extraction
            agent = self.get_or_create_agent(
                "generic-extractor", GenericDocumentExtraction
            )
            result = agent.extract(file_path)  # type: ignore

            # Handle both Pydantic model and dict responses
            if hasattr(result.data, "model_dump"):
                data = result.data.model_dump()
            elif isinstance(result.data, dict):
                data = result.data
            else:
                data = {"raw": str(result.data)}

            return {"schema": "generic", "data": data}

    async def extract(self, file_path: str, schema: Type[T], agent_name: str) -> T:
        """
        Extract with an explicit schema.

        Args:
            file_path: Path to the document file
            schema: Pydantic model class defining extraction schema
            agent_name: Name for the extraction agent

        Returns:
            Extracted data as the schema type
        """
        agent = self.get_or_create_agent(agent_name, schema)
        result = agent.extract(file_path)  # type: ignore
        return result.data

    async def extract_batch(self, file_paths: list[str]) -> list[dict]:
        """
        Extract from multiple files using inference.

        Args:
            file_paths: List of file paths to extract from

        Returns:
            List of extraction results with file, success status, and data
        """
        results = []
        for path in file_paths:
            try:
                result = await self.infer_and_extract(path)
                results.append({"file": path, "success": True, **result})
            except Exception as e:
                logger.error(f"Extraction failed for {path}: {e}")
                results.append({"file": path, "success": False, "error": str(e)})
        return results


# Singleton pattern
_llama_extract_service: Optional[LlamaExtractService] = None


def get_llama_extract_service() -> LlamaExtractService:
    """Get cached LlamaExtract service instance."""
    global _llama_extract_service
    if _llama_extract_service is None:
        _llama_extract_service = LlamaExtractService()
    return _llama_extract_service


def reset_llama_extract_service() -> None:
    """Reset service for testing."""
    global _llama_extract_service
    _llama_extract_service = None
