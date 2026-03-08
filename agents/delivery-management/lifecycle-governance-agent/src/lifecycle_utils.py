"""
Utility and helper functions for the Project Lifecycle & Governance Agent.

These are stateless helpers or methods that operate on agent state
passed explicitly via the ``agent`` parameter.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from project_lifecycle_agent import ProjectLifecycleAgent


# ---------------------------------------------------------------------------
# Methodology helpers
# ---------------------------------------------------------------------------


async def load_methodology_map(
    agent: ProjectLifecycleAgent, methodology: str, *, tenant_id: str = "default"
) -> dict[str, Any]:
    """Load methodology map with phases and gates."""
    stored_map = agent.persistence.load_methodology_map(tenant_id, methodology)
    if stored_map:
        return stored_map
    if methodology in agent.methodology_maps:
        return agent.methodology_maps[methodology]

    if methodology == "adaptive":
        return {
            "initial_phase": "Sprint 0",
            "phases": {
                "Sprint 0": {
                    "name": "Sprint 0",
                    "next_phases": ["Sprint 1"],
                    "gates": ["sprint_planning_complete"],
                },
                "Sprint 1": {
                    "name": "Sprint 1",
                    "next_phases": ["Sprint 2", "Release"],
                    "gates": ["sprint_review", "sprint_retrospective"],
                },
                "Release": {
                    "name": "Release",
                    "next_phases": [],
                    "gates": ["release_criteria_met"],
                },
            },
        }
    if methodology == "predictive":
        return {
            "initial_phase": "Initiate",
            "phases": {
                "Initiate": {
                    "name": "Initiate",
                    "next_phases": ["Plan"],
                    "gates": ["charter_approved"],
                },
                "Plan": {
                    "name": "Plan",
                    "next_phases": ["Execute"],
                    "gates": ["baseline_approved"],
                },
                "Execute": {
                    "name": "Execute",
                    "next_phases": ["Monitor", "Close"],
                    "gates": ["deliverables_complete"],
                },
                "Monitor": {
                    "name": "Monitor",
                    "next_phases": ["Close"],
                    "gates": ["acceptance_complete"],
                },
                "Close": {"name": "Close", "next_phases": [], "gates": ["closure_approved"]},
            },
        }
    return {
        "initial_phase": "Initiate",
        "phases": {
            "Initiate": {
                "name": "Initiate",
                "next_phases": ["Plan"],
                "gates": ["charter_approved"],
            },
            "Plan": {
                "name": "Plan",
                "next_phases": ["Iterate"],
                "gates": ["baseline_approved"],
            },
            "Iterate": {
                "name": "Iterate",
                "next_phases": ["Release", "Iterate"],
                "gates": ["iteration_complete"],
            },
            "Release": {
                "name": "Release",
                "next_phases": ["Close"],
                "gates": ["release_approved"],
            },
            "Close": {"name": "Close", "next_phases": [], "gates": ["closure_approved"]},
        },
    }


async def get_alternative_methodologies(primary: str) -> list[str]:
    """Get alternative methodologies."""
    all_methodologies = ["adaptive", "predictive", "hybrid"]
    return [m for m in all_methodologies if m != primary]


async def map_phase_to_methodology(
    agent: ProjectLifecycleAgent,
    current_phase: str,
    old_methodology: str,
    new_methodology: str,
    *,
    tenant_id: str,
) -> str:
    """Map current phase to equivalent in new methodology."""
    new_map = await load_methodology_map(agent, new_methodology, tenant_id=tenant_id)
    if current_phase in new_map.get("phases", {}):
        return current_phase
    phase_map = new_map.get("phase_map", {}).get(old_methodology, {})
    mapped = phase_map.get(current_phase)
    if mapped:
        return mapped
    return new_map["initial_phase"]  # type: ignore


# ---------------------------------------------------------------------------
# Gate helpers
# ---------------------------------------------------------------------------


async def get_gate_name(from_phase: str, to_phase: str) -> str:
    """Get gate name for phase transition."""
    return f"{from_phase}_to_{to_phase}_gate"


async def get_gate_criteria(
    agent: ProjectLifecycleAgent, gate_name: str, *, tenant_id: str
) -> list[str]:
    """Get criteria for a specific gate."""
    stored = agent.persistence.load_gate_criteria(tenant_id, gate_name)
    if stored:
        return stored
    if gate_name in agent.gate_criteria:
        return agent.gate_criteria[gate_name]
    normalized_gate = gate_name.lower().replace(" ", "_")
    transition_defaults = {
        "initiate_to_plan_gate": [
            "charter_document_complete",
            "charter_approved",
            "sponsor_assigned",
        ],
        "plan_to_execute_gate": [
            "scope_baseline_approved",
            "schedule_baseline_approved",
            "budget_approved",
        ],
        "plan_to_iterate_gate": [
            "scope_baseline_approved",
            "schedule_baseline_approved",
            "budget_approved",
        ],
        "iterate_to_release_gate": ["iteration_complete", "release_criteria_met"],
        "release_to_close_gate": ["release_criteria_met", "closure_approved"],
        "execute_to_monitor_gate": ["deliverables_complete", "quality_criteria_met"],
        "execute_to_close_gate": ["deliverables_complete", "quality_criteria_met"],
        "monitor_to_close_gate": ["acceptance_complete"],
        "sprint_0_to_sprint_1_gate": ["sprint_planning_complete"],
        "sprint_1_to_sprint_2_gate": [
            "sprint_review_complete",
            "sprint_retrospective_complete",
        ],
        "sprint_1_to_release_gate": [
            "sprint_review_complete",
            "sprint_retrospective_complete",
            "release_criteria_met",
        ],
    }
    if normalized_gate in transition_defaults:
        return transition_defaults[normalized_gate]
    explicit_defaults = {
        "charter_approved": [
            "charter_document_complete",
            "charter_approved",
            "sponsor_assigned",
        ],
        "baseline_approved": [
            "scope_baseline_approved",
            "schedule_baseline_approved",
            "budget_approved",
        ],
        "deliverables_complete": ["deliverables_complete", "quality_criteria_met"],
        "acceptance_complete": ["acceptance_complete"],
        "closure_approved": ["closure_approved"],
        "iteration_complete": ["iteration_complete"],
        "release_approved": ["release_approved"],
        "release_criteria_met": ["release_criteria_met"],
        "sprint_planning_complete": ["sprint_planning_complete"],
        "sprint_review": ["sprint_review_complete"],
        "sprint_retrospective": ["sprint_retrospective_complete"],
    }
    if normalized_gate in explicit_defaults:
        return explicit_defaults[normalized_gate]
    if "charter" in normalized_gate:
        return ["charter_document_complete", "charter_approved", "sponsor_assigned"]
    if "baseline" in normalized_gate:
        return ["scope_baseline_approved", "schedule_baseline_approved", "budget_approved"]
    return ["deliverables_complete", "quality_criteria_met"]


async def check_criterion(agent: ProjectLifecycleAgent, project_id: str, criterion: str) -> bool:
    """Check if a specific criterion is met."""
    project = agent.projects.get(project_id, {})
    artifacts = project.get("artifacts", {})
    approvals = project.get("approvals", {})
    metrics = project.get("metrics", {})

    criteria_map = {
        "charter_document_complete": artifacts.get("charter", {}).get("complete", False),
        "charter_approved": approvals.get("charter", False),
        "sponsor_assigned": bool(project.get("sponsor")),
        "scope_baseline_approved": approvals.get("scope_baseline", False),
        "schedule_baseline_approved": approvals.get("schedule_baseline", False),
        "budget_approved": approvals.get("budget", False),
        "deliverables_complete": artifacts.get("deliverables", {}).get("complete", False),
        "quality_criteria_met": metrics.get("quality_score", 0) >= 0.85,
        "acceptance_complete": approvals.get("acceptance", False),
        "closure_approved": approvals.get("closure", False),
        "iteration_complete": artifacts.get("iteration", {}).get("complete", False),
        "release_approved": approvals.get("release", False),
        "release_criteria_met": artifacts.get("release", {}).get("criteria_met", False)
        or approvals.get("release", False),
        "sprint_planning_complete": artifacts.get("sprint_plan", {}).get("complete", False),
        "sprint_review_complete": artifacts.get("sprint_review", {}).get("complete", False),
        "sprint_retrospective_complete": artifacts.get("sprint_retro", {}).get("complete", False),
    }

    return bool(criteria_map.get(criterion, False))


async def get_criterion_description(criterion: str) -> str:
    """Get description for a criterion."""
    descriptions = {
        "charter_document_complete": "Project charter document is complete with all sections filled",
        "charter_approved": "Project charter has been approved by sponsor",
        "sponsor_assigned": "Project sponsor has been assigned",
        "scope_baseline_approved": "Scope baseline has been approved",
        "schedule_baseline_approved": "Schedule baseline has been approved",
        "budget_approved": "Project budget has been approved",
        "deliverables_complete": "All phase deliverables are complete",
        "quality_criteria_met": "Quality criteria have been met",
        "acceptance_complete": "Client acceptance has been documented",
        "closure_approved": "Project closure has been approved",
        "iteration_complete": "Iteration deliverables have been completed",
        "release_approved": "Release approval has been granted",
        "release_criteria_met": "Release readiness criteria have been met",
        "sprint_planning_complete": "Sprint planning artifacts are complete",
        "sprint_review_complete": "Sprint review has been completed",
        "sprint_retrospective_complete": "Sprint retrospective has been completed",
    }
    return descriptions.get(criterion, criterion)


async def get_pending_gates(agent: ProjectLifecycleAgent, project_id: str) -> list[str]:
    """Get list of pending gates."""
    lifecycle_state = agent.lifecycle_states.get(project_id)
    if not lifecycle_state:
        return []

    current_phase = lifecycle_state.get("current_phase")
    methodology_map = lifecycle_state.get("methodology_map", {})

    phase_info = methodology_map.get("phases", {}).get(current_phase, {})
    return phase_info.get("gates", [])  # type: ignore


# ---------------------------------------------------------------------------
# Health helpers
# ---------------------------------------------------------------------------


async def determine_health_status(composite_score: float) -> str:
    """Determine health status from composite score."""
    if composite_score >= 0.85:
        return "Healthy"
    elif composite_score >= 0.70:
        return "At Risk"
    else:
        return "Critical"


async def get_metric_status(score: float) -> str:
    """Get status for individual metric."""
    if score >= 0.85:
        return "green"
    elif score >= 0.70:
        return "yellow"
    else:
        return "red"


async def detect_warnings(
    agent: ProjectLifecycleAgent, project_id: str, raw_metrics: dict[str, float | None]
) -> list[dict[str, Any]]:
    """Detect early warning signals."""
    project = agent.projects.get(project_id, {})
    warnings: list[dict[str, Any]] = []

    schedule_variance = raw_metrics.get("schedule_variance")
    if schedule_variance is not None and schedule_variance < -0.1:
        warnings.append(
            {
                "type": "schedule_slip",
                "message": "Schedule slipping beyond 10% threshold",
            }
        )

    cost_variance = raw_metrics.get("cost_variance")
    if cost_variance is not None and cost_variance > 0.1:
        warnings.append(
            {
                "type": "cost_overrun",
                "message": "Cost variance exceeds 10% threshold",
            }
        )

    risk = project.get("risk", {})
    if risk.get("open_risks", 0) >= 5:
        warnings.append(
            {
                "type": "risk_backlog",
                "message": "Risk backlog exceeds 5 open items",
            }
        )

    quality = project.get("quality", {})
    if quality.get("defects", 0) > 10:
        warnings.append(
            {
                "type": "quality_issues",
                "message": "High defect rate detected",
            }
        )

    resource_utilization = raw_metrics.get("resource_utilization")
    if resource_utilization is not None and resource_utilization > 0.95:
        warnings.append(
            {
                "type": "resource_overload",
                "message": "Resource utilization exceeds 95%",
            }
        )

    return warnings


async def generate_health_trends(
    agent: ProjectLifecycleAgent, project_id: str, *, tenant_id: str
) -> dict[str, Any]:
    """Generate health trend data from historical health scores."""
    history = [
        record
        for record in agent.health_store.list(tenant_id)
        if record.get("project_id") == project_id
    ]
    history = sorted(history, key=lambda record: record.get("monitored_at", ""))

    def _trend(values: list[float]) -> str:
        if len(values) < 2:
            return "stable"
        if values[-1] > values[0]:
            return "improving"
        if values[-1] < values[0]:
            return "declining"
        return "stable"

    schedule_values = [
        record.get("metrics", {}).get("schedule", {}).get("score", 0) for record in history
    ]
    cost_values = [record.get("metrics", {}).get("cost", {}).get("score", 0) for record in history]
    risk_values = [record.get("metrics", {}).get("risk", {}).get("score", 0) for record in history]
    quality_values = [
        record.get("metrics", {}).get("quality", {}).get("score", 0) for record in history
    ]
    resource_values = [
        record.get("metrics", {}).get("resource", {}).get("score", 0) for record in history
    ]

    return {
        "schedule_trend": _trend(schedule_values),
        "cost_trend": _trend(cost_values),
        "risk_trend": _trend(risk_values),
        "quality_trend": _trend(quality_values),
        "resource_trend": _trend(resource_values),
        "history": history[-10:],
    }


async def generate_alerts(health_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate alerts based on health data."""
    alerts: list[dict[str, Any]] = []
    if health_data.get("health_status") == "Critical":
        alerts.append(
            {
                "severity": "high",
                "message": "Project health is critical. Immediate action required.",
                "recommended_action": "Escalate to PMO and steering committee",
            }
        )
    return alerts


# ---------------------------------------------------------------------------
# Lifecycle state helpers
# ---------------------------------------------------------------------------


async def get_lifecycle_state(
    agent: ProjectLifecycleAgent, tenant_id: str, project_id: str
) -> dict[str, Any] | None:
    lifecycle_state = agent.lifecycle_states.get(project_id)
    if not lifecycle_state:
        lifecycle_state = agent.lifecycle_store.get(tenant_id, project_id)
        if lifecycle_state:
            agent.lifecycle_states[project_id] = lifecycle_state
    return lifecycle_state


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------


async def bootstrap_configuration(agent: ProjectLifecycleAgent) -> None:
    for methodology, methodology_map in agent.methodology_maps.items():
        if not agent.persistence.load_methodology_map("default", methodology):
            agent.persistence.store_methodology_map("default", methodology, methodology_map)
    for gate_name, criteria in agent.gate_criteria.items():
        if not agent.persistence.load_gate_criteria("default", gate_name):
            agent.persistence.store_gate_criteria("default", gate_name, criteria)


async def update_methodology_config(
    agent: ProjectLifecycleAgent,
    *,
    tenant_id: str,
    methodology: str | None,
    methodology_map: dict[str, Any] | None,
    gate_name: str | None,
    gate_criteria: list[str] | None,
) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if methodology and methodology_map:
        record = agent.persistence.store_methodology_map(tenant_id, methodology, methodology_map)
        updates["methodology_map"] = record
    if gate_name and gate_criteria:
        record = agent.persistence.store_gate_criteria(tenant_id, gate_name, gate_criteria)
        updates["gate_criteria"] = record
    return {"status": "updated", "updates": updates}


# ---------------------------------------------------------------------------
# Event publishing helpers
# ---------------------------------------------------------------------------


async def publish_project_transitioned(
    agent: ProjectLifecycleAgent,
    project_id: str,
    from_stage: str,
    to_stage: str,
    actor_id: str,
    *,
    tenant_id: str,
    correlation_id: str,
) -> None:
    import uuid as _uuid

    try:
        from events import ProjectTransitionedEvent
    except Exception:
        from packages.contracts.src.events import ProjectTransitionedEvent

    from observability.tracing import get_trace_id

    event = ProjectTransitionedEvent(
        event_name="project.transitioned",
        event_id=f"evt-{_uuid.uuid4().hex}",
        timestamp=datetime.now(timezone.utc),
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        trace_id=get_trace_id(),
        payload={
            "project_id": project_id,
            "from_stage": from_stage,
            "to_stage": to_stage,
            "transitioned_at": datetime.now(timezone.utc),
            "actor_id": actor_id,
        },
    )
    await agent.event_bus.publish("project.transitioned", event.model_dump())


async def publish_health_updated(
    agent: ProjectLifecycleAgent,
    project_id: str,
    health_data: dict[str, Any],
    *,
    tenant_id: str,
) -> None:
    import uuid as _uuid

    try:
        from events import ProjectHealthUpdatedEvent
    except Exception:
        from packages.contracts.src.events import ProjectHealthUpdatedEvent

    from observability.tracing import get_trace_id

    event = ProjectHealthUpdatedEvent(
        event_name="project.health.updated",
        event_id=f"evt-{_uuid.uuid4().hex}",
        timestamp=datetime.now(timezone.utc),
        tenant_id=tenant_id,
        trace_id=get_trace_id(),
        payload={
            "project_id": project_id,
            "health_data": health_data,
        },
    )
    await agent.event_bus.publish("project.health.updated", event.model_dump())


async def publish_health_report_generated(
    agent: ProjectLifecycleAgent, report: dict[str, Any], *, tenant_id: str
) -> None:
    import uuid as _uuid

    try:
        from events import ProjectHealthReportGeneratedEvent
    except Exception:
        from packages.contracts.src.events import ProjectHealthReportGeneratedEvent

    from observability.tracing import get_trace_id

    event = ProjectHealthReportGeneratedEvent(
        event_name="project.health.report.generated",
        event_id=f"evt-{_uuid.uuid4().hex}",
        timestamp=datetime.now(timezone.utc),
        tenant_id=tenant_id,
        trace_id=get_trace_id(),
        payload={"report": report},
    )
    await agent.event_bus.publish("project.health.report.generated", event.model_dump())
