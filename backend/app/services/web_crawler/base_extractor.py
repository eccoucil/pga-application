"""Abstract base class for LLM-based extractors.

Implements the Template Method pattern so each sub-agent only needs to
override content preparation and result parsing while sharing API call
logic, JSON extraction, and error handling.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, TypeVar

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.services.web_crawler.llm_utils import extract_json_from_response

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseLLMExtractor(ABC):
    """Template base for all LLM-powered extractors.

    Subclasses must implement:
        - ``SYSTEM_PROMPT`` class attribute
        - ``_prepare_content()`` — build the user message from pages
        - ``_parse_result()`` — convert parsed JSON into the domain model
        - ``_empty_result()`` — fallback when no pages or LLM errors occur
    """

    SYSTEM_PROMPT: str  # Override in subclass

    def __init__(self, client: anthropic.AsyncAnthropic, model: str) -> None:
        self.client = client
        self.model = model

    # ------------------------------------------------------------------
    # Template method
    # ------------------------------------------------------------------

    async def extract(self, pages: list, **kwargs: Any) -> Any:
        """Run the full extract pipeline: prepare → call LLM → parse.

        Args:
            pages: List of ``PageData`` objects from the crawl.
            **kwargs: Forwarded to ``_prepare_content`` (e.g. ``base_domain``).

        Returns:
            Domain-specific result, or ``_empty_result()`` on failure.
        """
        if not pages:
            return self._empty_result()

        content = self._prepare_content(pages, **kwargs)

        try:
            data = await self._call_llm(content)
        except Exception as e:
            logger.error(f"{self.__class__.__name__} LLM call failed: {e}")
            return self._empty_result()

        try:
            return self._parse_result(data, pages, **kwargs)
        except Exception as e:
            logger.error(f"{self.__class__.__name__} parse failed: {e}")
            return self._empty_result()

    # ------------------------------------------------------------------
    # LLM interaction (shared)
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type(
            (anthropic.RateLimitError, anthropic.APITimeoutError)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _call_llm(self, user_content: str) -> Any:
        """Call the Anthropic API and return parsed JSON.

        Retries up to 3 times on rate-limit or timeout errors with
        exponential backoff.

        Args:
            user_content: The full user message to send.

        Returns:
            Parsed JSON (dict or list).

        Raises:
            Exception: On API or JSON parsing errors.
        """
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self._max_tokens(),
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        raw_text = response.content[0].text
        return extract_json_from_response(raw_text, expect_array=self._expect_array())

    # ------------------------------------------------------------------
    # Hooks for subclasses
    # ------------------------------------------------------------------

    @abstractmethod
    def _prepare_content(self, pages: list, **kwargs: Any) -> str:
        """Build the user-message string from crawled pages."""

    @abstractmethod
    def _parse_result(self, data: Any, pages: list, **kwargs: Any) -> Any:
        """Convert parsed JSON into the domain model."""

    @abstractmethod
    def _empty_result(self) -> Any:
        """Return a safe default when extraction cannot proceed."""

    def _max_tokens(self) -> int:
        """Override to change max_tokens for the LLM call."""
        return 2000

    def _expect_array(self) -> bool:
        """Override to ``True`` if the LLM should return a JSON array."""
        return False
