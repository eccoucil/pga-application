"""Tests for app.services.web_crawler.llm_utils."""

import json

import pytest

from app.services.web_crawler.llm_utils import extract_json_from_response


class TestExtractJsonFromResponse:
    """JSON extraction from LLM text responses."""

    def test_fenced_json_object(self):
        text = 'Here is the result:\n```json\n{"key": "value"}\n```\nDone.'
        assert extract_json_from_response(text) == {"key": "value"}

    def test_fenced_json_array(self):
        text = '```json\n[{"a": 1}, {"a": 2}]\n```'
        assert extract_json_from_response(text, expect_array=True) == [
            {"a": 1},
            {"a": 2},
        ]

    def test_raw_object(self):
        text = 'The data is {"name": "Acme"} as shown.'
        assert extract_json_from_response(text) == {"name": "Acme"}

    def test_raw_array(self):
        text = 'Found: [{"url": "https://x.com"}]'
        assert extract_json_from_response(text, expect_array=True) == [
            {"url": "https://x.com"}
        ]

    def test_pure_json(self):
        obj = {"hello": "world", "items": [1, 2]}
        assert extract_json_from_response(json.dumps(obj)) == obj

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            extract_json_from_response("no json here at all")

    def test_nested_json_in_fence(self):
        nested = {"outer": {"inner": [1, 2, 3]}}
        text = f"```json\n{json.dumps(nested)}\n```"
        assert extract_json_from_response(text) == nested

    def test_fence_preferred_over_raw(self):
        """When both fenced and raw JSON exist, fenced should win."""
        text = '{"raw": true}\n```json\n{"fenced": true}\n```'
        result = extract_json_from_response(text)
        assert result == {"fenced": True}

    def test_multiline_fenced_json(self):
        text = """```json
{
    "company_name": "Test Corp",
    "industry": "Technology",
    "key_services": ["SaaS", "PaaS"]
}
```"""
        result = extract_json_from_response(text)
        assert result["company_name"] == "Test Corp"
        assert len(result["key_services"]) == 2
