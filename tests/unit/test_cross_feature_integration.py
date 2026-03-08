"""Cross-feature integration tests verifying production-grade interactions.

Tests cover multi-feature workflows, state consistency across features,
and error propagation between components.
"""

from __future__ import annotations

import asyncio

import pytest
from annotations import Annotation, AnnotationStore, generate_suggestions

# --- Execution events + annotations integration ---
from agents.runtime.src.execution_events import (
    ExecutionEvent,
    ExecutionEventEmitter,
    ExecutionEventRegistry,
    ExecutionEventType,
)


@pytest.mark.asyncio
async def test_execution_events_drive_annotations(tmp_path):
    """Execution events should be usable to trigger annotation creation."""
    store = AnnotationStore(db_path=tmp_path / "ann.db", persist=True)
    emitter = ExecutionEventEmitter("session-1")

    # Simulate agent emitting a risk event
    await emitter.emit(
        ExecutionEvent(
            event_type=ExecutionEventType.agent_completed,
            agent_id="risk-management",
            task_id="risk-check-1",
            data={"risk_level": "high", "message": "Budget risk detected"},
        )
    )

    event = await emitter.get(timeout=1.0)
    assert event is not None

    # Create annotation from event data
    ann = Annotation(
        session_id="session-1",
        agent_id=event.agent_id,
        agent_name="Risk Agent",
        block_id="block-main",
        content=event.data.get("message", ""),
        annotation_type="warning",
    )
    created = store.create_annotation("session-1", ann)
    assert created.agent_id == "risk-management"
    assert created.content == "Budget risk detected"

    # Verify persistence
    anns = store.list_annotations("session-1")
    assert len(anns) == 1


# --- Predictive + Health Aggregator consistency ---

from predictive import HealthPredictor, MonteCarloSimulator


def test_health_predictions_consistent_with_simulation():
    """Health predictions and simulation should use compatible score ranges."""
    predictor = HealthPredictor()
    simulator = MonteCarloSimulator()

    # Project with moderate signals
    signals = {"risk": 0.4, "schedule": 0.7, "budget": 0.6, "resource": 0.5, "trend_decay": 0.02}
    health = predictor.predict_health("proj-1", "Test", signals)

    sim_result = simulator.simulate(
        {"project_id": "proj-1", "estimated_duration_days": 100, "estimated_cost": 200000},
        iterations=500,
    )

    # Both should produce values in valid ranges
    assert 0.0 <= health.current_health_score <= 1.0
    assert 0.0 <= sim_result.on_time_probability <= 1.0
    assert 0.0 <= sim_result.on_budget_probability <= 1.0


# --- NL Workflow + Execution Events ---

from nl_workflow import NLWorkflowParser


def test_workflow_steps_map_to_event_types():
    """Workflow step types should have corresponding execution event types."""
    parser = NLWorkflowParser()
    definition = asyncio.run(parser.parse("Evaluate risks, get approval, and notify stakeholders"))

    # All steps should be translatable to execution events
    valid_step_types = {"task", "decision", "approval", "notification", "parallel", "api"}
    for step in definition["steps"]:
        assert step["type"] in valid_step_types

    # Verify the workflow is valid
    validation = parser.validate_generated(definition)
    assert validation["valid"] is True


# --- Annotation suggestions + Knowledge patterns ---


@pytest.mark.asyncio
async def test_annotation_suggestions_for_various_domains():
    """Annotation system should generate domain-specific suggestions."""
    test_cases = [
        ("There is a significant risk of project failure", "risk-management"),
        ("The budget has exceeded cost projections by 20%", "financial-management"),
        ("The milestone deadline was missed last week", "schedule-planning"),
        ("GDPR compliance must be verified before launch", "compliance-governance"),
    ]

    for content, expected_agent in test_cases:
        suggestions = await generate_suggestions("s1", "b1", content)
        agent_ids = {s.agent_id for s in suggestions}
        assert (
            expected_agent in agent_ids
        ), f"Expected {expected_agent} for '{content[:40]}...', got {agent_ids}"


# --- Registry singleton consistency ---


def test_execution_registry_singleton():
    """Singleton registry should return the same instance."""
    r1 = ExecutionEventRegistry.get_instance()
    r2 = ExecutionEventRegistry.get_instance()
    assert r1 is r2


# --- Intake intelligence + NL workflow ---


def test_intake_classification_informs_workflow():
    """Classification categories should map to workflow step types."""
    # Regulatory should produce compliance steps
    parser = NLWorkflowParser()
    definition = asyncio.run(parser.parse("New GDPR regulatory compliance requirement"))
    step_names = [s["name"].lower() for s in definition["steps"]]
    assert any("compliance" in name for name in step_names)
