"""Tests for app.services.web_crawler.base_extractor."""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.web_crawler import PageData
from app.services.web_crawler.base_extractor import BaseLLMExtractor


def _make_page(url: str = "https://example.com") -> PageData:
    return PageData(
        url=url,
        title="Test",
        content="Some content here",
        word_count=3,
        links=[],
        crawl_timestamp=datetime.utcnow(),
    )


class ConcreteExtractor(BaseLLMExtractor):
    """Minimal concrete implementation for testing."""

    SYSTEM_PROMPT = "You are a test extractor."

    def _prepare_content(self, pages: list, **kwargs: Any) -> str:
        return "\n".join(p.content for p in pages)

    def _parse_result(self, data: Any, pages: list, **kwargs: Any) -> dict:
        return {"parsed": True, "data": data}

    def _empty_result(self) -> dict:
        return {"parsed": False, "data": None}


class ArrayExtractor(BaseLLMExtractor):
    """Concrete extractor that expects arrays."""

    SYSTEM_PROMPT = "Return an array."

    def _prepare_content(self, pages: list, **kwargs: Any) -> str:
        return "content"

    def _parse_result(self, data: Any, pages: list, **kwargs: Any) -> list:
        return data

    def _empty_result(self) -> list:
        return []

    def _expect_array(self) -> bool:
        return True

    def _max_tokens(self) -> int:
        return 5000


def _mock_client(response_text: str) -> MagicMock:
    """Create a mock Anthropic client that returns *response_text*."""
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=response_text)]
    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=mock_msg)
    return client


@pytest.mark.asyncio
class TestBaseLLMExtractor:
    async def test_empty_pages_returns_empty_result(self):
        client = _mock_client("{}")
        ext = ConcreteExtractor(client, "test-model")
        result = await ext.extract([])
        assert result == {"parsed": False, "data": None}
        client.messages.create.assert_not_called()

    async def test_successful_extraction(self):
        client = _mock_client('```json\n{"key": "value"}\n```')
        ext = ConcreteExtractor(client, "test-model")
        result = await ext.extract([_make_page()])
        assert result["parsed"] is True
        assert result["data"] == {"key": "value"}

    async def test_api_error_returns_empty_result(self):
        client = MagicMock()
        client.messages = MagicMock()
        client.messages.create = AsyncMock(side_effect=RuntimeError("API down"))
        ext = ConcreteExtractor(client, "test-model")
        result = await ext.extract([_make_page()])
        assert result == {"parsed": False, "data": None}

    async def test_parse_error_returns_empty_result(self):
        """If _parse_result raises, we get _empty_result."""
        client = _mock_client('{"valid": "json"}')

        class FailingParser(ConcreteExtractor):
            def _parse_result(self, data: Any, pages: list, **kwargs: Any) -> dict:
                raise ValueError("parse boom")

        ext = FailingParser(client, "test-model")
        result = await ext.extract([_make_page()])
        assert result == {"parsed": False, "data": None}

    async def test_array_extractor(self):
        client = _mock_client('[{"a": 1}]')
        ext = ArrayExtractor(client, "test-model")
        result = await ext.extract([_make_page()])
        assert result == [{"a": 1}]

    async def test_kwargs_forwarded(self):
        """Extra kwargs passed to extract() reach _prepare_content()."""
        client = _mock_client('{"ok": true}')

        class KwargsCapture(ConcreteExtractor):
            captured_kwargs: dict = {}

            def _prepare_content(self, pages: list, **kwargs: Any) -> str:
                KwargsCapture.captured_kwargs = kwargs
                return "content"

        ext = KwargsCapture(client, "test-model")
        await ext.extract([_make_page()], base_domain="example.com")
        assert KwargsCapture.captured_kwargs["base_domain"] == "example.com"

    async def test_llm_call_parameters(self):
        """Verify model, max_tokens, and system prompt are sent correctly."""
        client = _mock_client('{"data": true}')
        ext = ConcreteExtractor(client, "my-model")
        await ext.extract([_make_page()])

        call_kwargs = client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "my-model"
        assert call_kwargs["max_tokens"] == 2000  # default
        assert call_kwargs["system"] == "You are a test extractor."
