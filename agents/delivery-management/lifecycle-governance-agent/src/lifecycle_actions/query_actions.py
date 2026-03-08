"""Action handlers for read-only query operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from lifecycle_utils import (
    generate_alerts,
    generate_health_trends,
    get_lifecycle_state,
    get_pending_gates,
)

if TYPE_CHECKING:
    from project_lifecycle_agent import ProjectLifecycleAgent


async def get_project_status(
    agent: ProjectLifecycleAgent, project_id: str, *, tenant_id: str
) -> dict[str, Any]:
    """Get current project status."""
    project = agent.projects.get(project_id)
    lifecycle_state = await get_lifecycle_state(agent, tenant_id, project_id)

    if not project or not lifecycle_state:
        raise ValueError(f"Project not found: {project_id}")

    # Get health data
    health_data = agent.health_scores.get(project_id, {})

    # Get pending gates
    pending = await get_pending_gates(agent, project_id)

    return {
        "project_id": project_id,
        "name": project.get("name"),
        "current_phase": project.get("current_phase"),
        "methodology": project.get("methodology"),
        "status": project.get("status"),
        "health_status": health_data.get("health_status", "Unknown"),
        "composite_score": health_data.get("composite_score", 0),
        "pending_gates": pending,
        "phase_start_date": lifecycle_state.get("phase_start_date"),
        "transitions_count": len(lifecycle_state.get("transitions", [])),
    }


async def get_health_dashboard(
    agent: ProjectLifecycleAgent, project_id: str, *, tenant_id: str
) -> dict[str, Any]:
    """Generate comprehensive health dashboard."""
    from lifecycle_actions.monitor_health import monitor_health

    health_data = await monitor_health(agent, project_id, tenant_id=tenant_id)
    project = agent.projects.get(project_id, {})
    lifecycle_state = await get_lifecycle_state(agent, tenant_id, project_id)
    project_status = {
        "project_id": project_id,
        "name": project.get("name"),
        "current_phase": project.get("current_phase"),
        "methodology": project.get("methodology"),
        "status": project.get("status"),
        "health_status": health_data.get("health_status", "Unknown"),
        "composite_score": health_data.get("composite_score", 0),
        "phase_start_date": (lifecycle_state.get("phase_start_date") if lifecycle_state else None),
        "transitions_count": (
            len(lifecycle_state.get("transitions", [])) if lifecycle_state else 0
        ),
    }

    # Generate trend data
    trends = await generate_health_trends(agent, project_id, tenant_id=tenant_id)

    # Generate alerts
    alerts = await generate_alerts(health_data)

    return {
        "project_id": project_id,
        "project_status": project_status,
        "health_data": health_data,
        "trends": trends,
        "alerts": alerts,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_gate_history(
    agent: ProjectLifecycleAgent, project_id: str, gate_name: str | None, *, tenant_id: str
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "gate_name": gate_name,
        "history": agent.persistence.list_gate_outcomes(tenant_id, project_id, gate_name),
    }


async def get_readiness_scores(
    agent: ProjectLifecycleAgent, project_id: str, *, tenant_id: str
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "readiness_scores": agent.persistence.list_readiness_scores(tenant_id, project_id),
    }


async def get_health_history(
    agent: ProjectLifecycleAgent, project_id: str, *, tenant_id: str
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "health_history": agent.persistence.list_health_metrics(tenant_id, project_id),
    }
