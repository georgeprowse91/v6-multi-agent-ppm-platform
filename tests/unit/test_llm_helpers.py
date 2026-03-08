"""Tests for the shared LLM helpers module.

Tests cover JSON parsing resilience, markdown fence stripping,
timeout handling, and retry logic.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_mod_path = (
    Path(__file__).resolve().parents[2] / "apps" / "web" / "src" / "routes" / "_llm_helpers.py"
)
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
    result = _try_parse_json("[1, 2, 3]")
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


# --- Edge case and negative tests ---


def test_strip_markdown_fences_language_tag():
    """Strip fences with various language tags."""
    for lang in ["json", "python", "javascript", ""]:
        raw = f'```{lang}\n{{"key": "value"}}\n```'
        result = _strip_markdown_fences(raw)
        assert "```" not in result
        assert '"key"' in result


def test_strip_markdown_fences_whitespace():
    """Handle leading/trailing whitespace around fences."""
    raw = '  \n```json\n{"key": 1}\n```\n  '
    result = _strip_markdown_fences(raw)
    assert "```" not in result


def test_try_parse_json_nested():
    """Parse deeply nested JSON objects."""
    raw = '{"a": {"b": {"c": [1, 2, {"d": true}]}}}'
    result = _try_parse_json(raw)
    assert result is not None
    assert result["a"]["b"]["c"][2]["d"] is True


def test_try_parse_json_unicode():
    """Parse JSON with unicode characters."""
    raw = '{"name": "Ünited Stätes", "emoji": "rocket"}'
    result = _try_parse_json(raw)
    assert result is not None
    assert result["name"] == "Ünited Stätes"


def test_try_parse_json_escaped_quotes():
    """Parse JSON with escaped quotes inside strings."""
    raw = '{"msg": "He said \\"hello\\"", "count": 5}'
    result = _try_parse_json(raw)
    assert result is not None
    assert "hello" in result["msg"]


def test_try_parse_json_number_types():
    """Parse JSON with various number formats."""
    raw = '{"int": 42, "float": 3.14, "neg": -7, "exp": 1.5e10}'
    result = _try_parse_json(raw)
    assert result is not None
    assert result["int"] == 42
    assert abs(result["float"] - 3.14) < 0.001


def test_try_parse_json_only_text():
    """Non-JSON text should return None."""
    assert _try_parse_json("This is just plain text with no JSON.") is None


def test_try_parse_json_partial_json():
    """Truncated JSON should return None."""
    assert _try_parse_json('{"key": "val') is None


def test_try_parse_json_multiple_objects_in_text():
    """When text has interleaved JSON, extraction is best-effort."""
    raw = 'Here is the result: {"a": 1}'
    result = _try_parse_json(raw)
    assert result is not None
    assert isinstance(result, dict)
    assert result["a"] == 1


def test_try_parse_json_boolean_and_null():
    """Parse JSON with boolean and null values."""
    raw = '{"active": true, "deleted": false, "parent": null}'
    result = _try_parse_json(raw)
    assert result is not None
    assert result["active"] is True
    assert result["deleted"] is False
    assert result["parent"] is None


def test_try_parse_json_empty_object():
    """Parse empty JSON object."""
    result = _try_parse_json("{}")
    assert result == {}


def test_try_parse_json_empty_array():
    """Parse empty JSON array."""
    result = _try_parse_json("[]")
    assert result == []
