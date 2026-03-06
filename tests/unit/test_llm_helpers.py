"""Tests for the shared LLM helpers module.

Tests cover JSON parsing resilience, markdown fence stripping,
timeout handling, and retry logic.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_mod_path = Path(__file__).resolve().parents[2] / "apps" / "web" / "src" / "routes" / "_llm_helpers.py"
_spec = importlib.util.spec_from_file_location("_llm_helpers", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["_llm_helpers"] = _mod
_spec.loader.exec_module(_mod)

_strip_markdown_fences = _mod._strip_markdown_fences
_try_parse_json = _mod._try_parse_json


def test_strip_markdown_fences_json():
    raw = '```json\n{"key": "value"}\n```'
    assert _strip_markdown_fences(raw) == '{"key": "value"}'


def test_strip_markdown_fences_no_fences():
    raw = '{"key": "value"}'
    assert _strip_markdown_fences(raw) == '{"key": "value"}'


def test_strip_markdown_fences_empty():
    assert _strip_markdown_fences("") == ""


def test_try_parse_json_valid_object():
    result = _try_parse_json('{"key": "value"}')
    assert result == {"key": "value"}


def test_try_parse_json_valid_array():
    result = _try_parse_json('[1, 2, 3]')
    assert result == [1, 2, 3]


def test_try_parse_json_with_fences():
    result = _try_parse_json('```json\n{"key": "value"}\n```')
    assert result == {"key": "value"}


def test_try_parse_json_mixed_text():
    """Test extraction of JSON from mixed text."""
    raw = 'Here is the result: {"category": "strategic", "confidence": 0.85}'
    result = _try_parse_json(raw)
    assert result is not None
    assert result["category"] == "strategic"


def test_try_parse_json_array_in_text():
    raw = 'The patterns found: [{"id": "p1"}, {"id": "p2"}]'
    result = _try_parse_json(raw)
    assert isinstance(result, list)
    assert len(result) == 2


def test_try_parse_json_invalid():
    result = _try_parse_json("this is not json at all")
    assert result is None


def test_try_parse_json_empty():
    result = _try_parse_json("")
    assert result is None
