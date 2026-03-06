"""Tests for the NL workflow parser (Enhancement 3).

Tests cover keyword-based parsing, validation, and refinement.
parse() and refine() are now async, so tests use asyncio.
"""

from __future__ import annotations

import asyncio

from nl_workflow import NLWorkflowParser


def _run(coro):
    """Helper to run async functions in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


def test_parse_returns_valid_definition():
    parser = NLWorkflowParser()
    definition = _run(parser.parse("Route incoming requests through risk assessment and approval"))
    assert "name" in definition
    assert "steps" in definition
    assert len(definition["steps"]) > 0
    for step in definition["steps"]:
        assert "id" in step
        assert "type" in step
        assert "name" in step


def test_parse_includes_risk_step():
    parser = NLWorkflowParser()
    definition = _run(parser.parse("Evaluate project risks before proceeding"))
    step_names = [s["name"].lower() for s in definition["steps"]]
    assert any("risk" in name for name in step_names)


def test_parse_includes_approval_step():
    parser = NLWorkflowParser()
    definition = _run(parser.parse("Get CFO approval for the budget"))
    step_types = [s["type"] for s in definition["steps"]]
    assert "approval" in step_types


def test_parse_includes_compliance_step():
    parser = NLWorkflowParser()
    definition = _run(parser.parse("Ensure GDPR compliance before data migration"))
    step_names = [s["name"].lower() for s in definition["steps"]]
    assert any("compliance" in name for name in step_names)


def test_validate_valid_definition():
    parser = NLWorkflowParser()
    definition = _run(parser.parse("test"))
    result = parser.validate_generated(definition)
    assert result["valid"] is True
    assert result["errors"] == []


def test_validate_missing_name():
    parser = NLWorkflowParser()
    result = parser.validate_generated({"name": "", "steps": [{"id": "s1", "type": "task", "name": "x", "transitions": []}]})
    assert result["valid"] is False


def test_validate_bad_transition():
    parser = NLWorkflowParser()
    result = parser.validate_generated({
        "name": "test",
        "steps": [
            {"id": "s1", "type": "task", "name": "x", "transitions": [{"target": "nonexistent"}]}
        ],
    })
    assert result["valid"] is False
    assert any("nonexistent" in e for e in result["errors"])


def test_refine_returns_definition():
    parser = NLWorkflowParser()
    original = _run(parser.parse("test"))
    refined = _run(parser.refine(original, "add a notification step"))
    assert "steps" in refined
