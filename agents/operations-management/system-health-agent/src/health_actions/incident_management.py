"""Action handlers for incident management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from health_integrations import (
    create_servicenow_incident,
    notify_incident_integrations,
    update_servicenow_incident,
)
from health_utils import generate_incident_id, sanitize_text

if TYPE_CHECKING:
    from system_health_agent import SystemHealthAgent


async def create_incident(
    agent: SystemHealthAgent, tenant_id: str, incident_data: dict[str, Any]
) -> dict[str, Any]:
    """Create system incident.  Returns incident ID."""
    incident_title = sanitize_text(incident_data.get("title", ""))
    agent.logger.info("Creating incident: %s", incident_title)

    incident_id = await generate_incident_id()

    incident = {
        "incident_id": incident_id,
        "title": incident_title,
        "description": sanitize_text(incident_data.get("description", "")),
        "severity": incident_data.get("severity", "medium"),
        "affected_services": incident_data.get("affected_services", []),
        "status": "open",
        "assignee": sanitize_text(incident_data.get("assignee", "")),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": sanitize_text(incident_data.get("reporter", "")),
    }

    agent.incidents[incident_id] = incident
    agent.incident_store.upsert(tenant_id, incident_id, incident.copy())

    await create_servicenow_incident(agent, incident)
    await notify_incident_integrations(agent, incident)
    if incident.get("servicenow_sys_id"):
        agent.incident_store.upsert(tenant_id, incident_id, incident.copy())

    return {
        "incident_id": incident_id,
        "title": incident["title"],
        "severity": incident["severity"],
        "status": "open",
        "assignee": incident.get("assignee"),
    }


async def analyze_root_cause(agent: SystemHealthAgent, incident_id: str) -> dict[str, Any]:
    """Perform root cause analysis for incident.  Returns analysis results."""
    agent.logger.info("Analyzing root cause for incident: %s", incident_id)

    incident = agent.incidents.get(incident_id)
    if not incident:
        raise ValueError(f"Incident not found: {incident_id}")

    affected_services = incident.get("affected_services", [])

    metrics_data = await _collect_incident_metrics(affected_services)
    logs_data = await _collect_incident_logs(affected_services)
    traces_data = await _collect_incident_traces(affected_services)

    correlations = await _correlate_incident_data(metrics_data, logs_data, traces_data)

    probable_causes = await _identify_probable_causes(correlations)

    recommendations = await _generate_incident_recommendations(probable_causes)

    return {
        "incident_id": incident_id,
        "probable_causes": probable_causes,
        "correlations": correlations,
        "recommendations": recommendations,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


async def resolve_incident(
    agent: SystemHealthAgent, tenant_id: str, incident_id: str, resolution: dict[str, Any]
) -> dict[str, Any]:
    """Resolve incident.  Returns resolution confirmation."""
    agent.logger.info("Resolving incident: %s", incident_id)

    incident = agent.incidents.get(incident_id)
    if not incident:
        raise ValueError(f"Incident not found: {incident_id}")

    incident["status"] = "resolved"
    incident["resolution"] = sanitize_text(resolution.get("description", ""))
    incident["resolved_by"] = sanitize_text(resolution.get("resolved_by", ""))
    incident["resolved_at"] = datetime.now(timezone.utc).isoformat()

    created_at = datetime.fromisoformat(incident.get("created_at"))
    resolved_at = datetime.now(timezone.utc)
    resolution_time = (resolved_at - created_at).total_seconds() / 60  # minutes

    incident["resolution_time_minutes"] = resolution_time
    agent.incident_store.upsert(tenant_id, incident_id, incident.copy())

    await update_servicenow_incident(agent, incident)

    return {
        "incident_id": incident_id,
        "status": "resolved",
        "resolution_time_minutes": resolution_time,
        "resolved_at": incident["resolved_at"],
    }


# ---------------------------------------------------------------------------
# Root-cause analysis stubs (placeholders from original)
# ---------------------------------------------------------------------------


async def _collect_incident_metrics(affected_services: list[str]) -> dict[str, Any]:
    """Collect metrics related to incident."""
    return {}


async def _collect_incident_logs(affected_services: list[str]) -> list[dict[str, Any]]:
    """Collect logs related to incident."""
    return []


async def _collect_incident_traces(affected_services: list[str]) -> list[dict[str, Any]]:
    """Collect traces related to incident."""
    return []


async def _correlate_incident_data(
    metrics: dict[str, Any], logs: list[dict[str, Any]], traces: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Correlate incident data sources."""
    return []


async def _identify_probable_causes(correlations: list[dict[str, Any]]) -> list[str]:
    """Identify probable causes from correlations."""
    return ["High database load", "Network latency spike"]


async def _generate_incident_recommendations(probable_causes: list[str]) -> list[str]:
    """Generate recommendations based on probable causes."""
    return ["Scale database resources", "Check network connectivity"]
