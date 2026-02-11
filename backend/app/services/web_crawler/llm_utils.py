"""Shared LLM response utilities for the web crawler package.

Consolidates the JSON-extraction logic that was duplicated across all three
LLM sub-agents (BusinessContextAnalyzer, AssetDiscoveryAgent,
OrganizationInfoExtractor).
"""

import json
import re
from typing import Any


def extract_json_from_response(text: str, *, expect_array: bool = False) -> Any:
    """Extract and parse JSON from an LLM response.

    LLMs frequently wrap JSON in markdown code fences (```json ... ```) or
    include preamble text.  This function tries, in order:

    1. Extract content inside ```json ... ``` fences.
    2. Find the first raw JSON object ``{...}`` or array ``[...]``.
    3. Parse the entire text as JSON (fallback).

    Args:
        text: Raw LLM response text.
        expect_array: When ``True``, prefer extracting a JSON array ``[...]``
            in step 2 rather than an object ``{...}``.

    Returns:
        Parsed Python object (dict or list).

    Raises:
        json.JSONDecodeError: If no valid JSON could be found.
    """
    # Step 1: fenced code block
    fence_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if fence_match:
        return json.loads(fence_match.group(1))

    # Step 2: raw JSON (array or object depending on expectation)
    if expect_array:
        raw_match = re.search(r"\[.*]", text, re.DOTALL)
    else:
        raw_match = re.search(r"\{.*}", text, re.DOTALL)

    if raw_match:
        return json.loads(raw_match.group(0))

    # Step 3: whole-text fallback
    return json.loads(text)
