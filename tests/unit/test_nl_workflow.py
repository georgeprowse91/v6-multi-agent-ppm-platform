"""Tests for the NL workflow parser (Enhancement 3).

Tests cover keyword-based parsing, validation, and refinement.
parse() and refine() are now async, so tests use asyncio.
"""

from __future__ import annotations

import asyncio

from nl_workflow import NLWorkflowParser


def _run(coro):
    """Helper to run async functions in sync tests."""
    return asyncio.run(coro)


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
    result = parser.validate_generated(
        {"name": "", "steps": [{"id": "s1", "type": "task", "name": "x", "transitions": []}]}
    )
    assert result["valid"] is False


def test_validate_bad_transition():
    parser = NLWorkflowParser()
    result = parser.validate_generated(
        {
            "name": "test",
            "steps": [
                {
                    "id": "s1",
                    "type": "task",
                    "name": "x",
                    "transitions": [{"target": "nonexistent"}],
                }
            ],
        }
    )
    assert result["valid"] is False
    assert any("nonexistent" in e for e in result["errors"])


def test_refine_returns_definition():
    parser = NLWorkflowParser()
    original = _run(parser.parse("test"))
    refined = _run(parser.refine(original, "add a notification step"))
    assert "steps" in refined


# --- Error path and edge case tests ---


def test_parse_includes_financial_step():
    """Budget/financial keywords should trigger financial review step."""
    parser = NLWorkflowParser()
    definition = _run(parser.parse("Review the budget and spending forecast"))
    step_names = [s["name"].lower() for s in definition["steps"]]
    assert any("financial" in name or "budget" in name for name in step_names)


def test_parse_always_has_intake_and_notification():
    """Every generated workflow should start with intake and end with notification."""
    parser = NLWorkflowParser()
    for desc in ["simple task", "risk review with approval", "compliance audit"]:
        definition = _run(parser.parse(desc))
        steps = definition["steps"]
        assert steps[0]["type"] == "task"
        assert steps[-1]["type"] == "notification"


def test_parse_step_ids_unique():
    """All step IDs in a generated workflow should be unique."""
    parser = NLWorkflowParser()
    definition = _run(
        parser.parse(
            "Evaluate risks, get executive approval, ensure GDPR compliance, and review budget"
        )
    )
    step_ids = [s["id"] for s in definition["steps"]]
    assert len(step_ids) == len(set(step_ids))


def test_parse_all_steps_have_transitions():
    """Every step except the last should have transitions."""
    parser = NLWorkflowParser()
    definition = _run(parser.parse("Risk assessment and compliance check"))
    steps = definition["steps"]
    for step in steps[:-1]:
        assert len(step.get("transitions", [])) > 0, f"Step {step['id']} has no transitions"
    assert steps[-1]["transitions"] == []


def test_validate_empty_definition():
    """Empty definitions should fail validation."""
    parser = NLWorkflowParser()
    result = parser.validate_generated({})
    assert result["valid"] is False
    assert len(result["errors"]) >= 1


def test_validate_no_steps():
    """Workflow with name but no steps should fail validation."""
    parser = NLWorkflowParser()
    result = parser.validate_generated({"name": "Empty", "steps": []})
    assert result["valid"] is False


def test_validate_valid_self_referencing_transition():
    """A step referencing itself in a transition should be valid (loop)."""
    parser = NLWorkflowParser()
    result = parser.validate_generated(
        {
            "name": "Loop workflow",
            "steps": [
                {
                    "id": "s1",
                    "type": "decision",
                    "name": "Check",
                    "transitions": [{"target": "s1", "condition": "retry"}, {"target": "s2"}],
                },
                {"id": "s2", "type": "notification", "name": "Done", "transitions": []},
            ],
        }
    )
    assert result["valid"] is True


def test_parse_multiple_keywords_combined():
    """Description with many keywords should produce a multi-step workflow."""
    parser = NLWorkflowParser()
    definition = _run(
        parser.parse(
            "Assess project risks, get CFO approval for budget spending, "
            "ensure SOX compliance, then execute"
        )
    )
    assert len(definition["steps"]) >= 5
    step_types = {s["type"] for s in definition["steps"]}
    assert "approval" in step_types
    assert "decision" in step_types


def test_parse_empty_description():
    """Empty description should still produce a valid minimal workflow."""
    parser = NLWorkflowParser()
    definition = _run(parser.parse(""))
    assert len(definition["steps"]) >= 2


def test_refine_preserves_structure():
    """Refine should return a workflow with the same structure (name, steps)."""
    parser = NLWorkflowParser()
    original = _run(parser.parse("Simple project workflow"))
    refined = _run(parser.refine(original, "make it longer"))
    assert "name" in refined
    assert "steps" in refined
    assert len(refined["steps"]) >= 1
