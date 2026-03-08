"""
Type definitions for the Continuous Improvement & Process Mining Agent.

Provides TypedDict definitions for the major data structures exchanged between
action handlers, utilities, and the main agent class.
"""

from __future__ import annotations

from typing import Any, Protocol, TypedDict


class TimeRange(TypedDict, total=False):
    start: str | None
    end: str | None


class TransitionRecord(TypedDict, total=False):
    """A single transition between two activities."""

    from_: str  # aliased from ``from`` in dicts
    to: str
    frequency: int


class ProcessModelPayload(TypedDict, total=False):
    activities: list[str]
    transitions: list[dict[str, Any]]
    algorithm: str


class BpmnModel(TypedDict, total=False):
    type: str
    start_events: list[dict[str, Any]]
    end_events: list[dict[str, Any]]
    tasks: list[dict[str, Any]]
    sequence_flows: list[dict[str, Any]]


class PetriNet(TypedDict, total=False):
    type: str
    places: list[dict[str, str]]
    transitions: list[dict[str, str]]
    arcs: list[dict[str, str]]


class ProcessMetrics(TypedDict, total=False):
    median_cycle_time: float
    throughput: int | float
    activity_count: int
    avg_waiting_time: float
    trace_count: int


class ImprovementRecord(TypedDict, total=False):
    improvement_id: str
    title: str | None
    description: str | None
    category: str | None
    process_id: str | None
    expected_benefits: dict[str, Any]
    feasibility: dict[str, Any]
    priority_score: float
    owner: str | None
    status: str
    created_at: str
    completed_at: str
    completed_by: str
    outcome: str
    source_report_id: str | None
    target_date: str
    target_due_date: str


class BenefitTracking(TypedDict, total=False):
    improvement_id: str
    expected_benefits: dict[str, Any]
    actual_benefits: dict[str, Any]
    realization_percentage: float
    measured_at: str


# ---------------------------------------------------------------------------
# Protocol used by action modules to type-hint the agent without importing
# the concrete class (avoids circular imports).
# ---------------------------------------------------------------------------


class MiningAgentProtocol(Protocol):
    """Structural interface that action modules may rely on."""

    agent_id: str
    logger: Any
    bottleneck_threshold: float
    deviation_threshold: float
    min_frequency_threshold: int
    mining_algorithms: list[str]
    event_log_store: Any
    process_model_store: Any
    conformance_store: Any
    recommendations_store: Any
    improvement_history_store: Any
    improvement_backlog_store: Any
    event_logs: dict[str, Any]
    process_models: dict[str, Any]
    improvement_backlog: dict[str, Any]
    benefit_tracking: dict[str, Any]
    benchmarks: dict[str, Any]
    event_log_index: dict[str, list[dict[str, Any]]]
    integration_clients: dict[str, Any]
    financial_agent: Any
    approval_workflow_agent: Any
    knowledge_agent: Any
    event_bus: Any
    max_deviation_alerts: int
    knowledge_event_topic: str
    default_improvement_owner: str
