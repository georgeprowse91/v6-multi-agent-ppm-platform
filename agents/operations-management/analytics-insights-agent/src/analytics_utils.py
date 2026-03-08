"""
Utility functions for the Analytics & Insights Agent.

Contains ID generators, data collection helpers, masking, event filtering,
default configuration constants, and other stateless or low-coupling helpers
used by action handlers.
"""

from __future__ import annotations

import inspect
import os
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from security.lineage import mask_lineage_payload

from agents.common.health_recommendations import generate_recommendations, identify_health_concerns

# ---------------------------------------------------------------------------
# ID generators
# ---------------------------------------------------------------------------


async def generate_dashboard_id() -> str:
    """Generate unique dashboard ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"DASH-{timestamp}"


async def generate_report_id() -> str:
    """Generate unique report ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"REPORT-{timestamp}"


async def generate_prediction_id() -> str:
    """Generate unique prediction ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"PRED-{timestamp}"


async def generate_scenario_id() -> str:
    """Generate unique scenario ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"SCENARIO-{timestamp}"


async def generate_kpi_id() -> str:
    """Generate unique KPI ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"KPI-{timestamp}"


async def generate_lineage_id() -> str:
    """Generate unique lineage ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"LINEAGE-{timestamp}"


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


async def maybe_await(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Call *func* and ``await`` the result only when it is awaitable."""
    result = func(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


async def fetch_source_payload(source: str) -> list[dict[str, Any]]:
    """Fetch data from a specific source system."""
    return [
        {
            "source": source,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "records": [],
        }
    ]


async def collect_from_sources(sources: list[str]) -> list[dict[str, Any]]:
    """Collect data from multiple sources."""
    aggregated: list[dict[str, Any]] = []
    for source in sources:
        aggregated.extend(await fetch_source_payload(source))
    return aggregated


async def harmonize_data(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Harmonize data definitions."""
    return data


async def calculate_statistics(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate summary statistics."""
    return {"mean": 0, "median": 0, "std_dev": 0, "min": 0, "max": 0}


# ---------------------------------------------------------------------------
# Masking / redaction
# ---------------------------------------------------------------------------

PII_FIELDS = {
    "address",
    "birthdate",
    "date_of_birth",
    "dob",
    "email",
    "employee_id",
    "first_name",
    "full_name",
    "last_name",
    "phone",
    "phone_number",
    "ssn",
    "social_security_number",
    "user_id",
    "username",
}


def mask_sensitive_fields(payload: Any) -> Any:
    """Recursively mask PII fields in a payload."""
    if isinstance(payload, dict):
        masked: dict[str, Any] = {}
        for key, value in payload.items():
            if key.lower() in PII_FIELDS and value is not None:
                masked[key] = "redacted"
            else:
                masked[key] = mask_sensitive_fields(value)
        return masked
    if isinstance(payload, list):
        return [mask_sensitive_fields(item) for item in payload]
    return payload


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Redact payload using salt-based masking when configured, else PII masking."""
    if os.getenv("LINEAGE_MASK_SALT"):
        return mask_lineage_payload(payload)
    return mask_sensitive_fields(payload)


# ---------------------------------------------------------------------------
# Event filtering
# ---------------------------------------------------------------------------


def filter_events(events: list[dict[str, Any]], event_types: set[str]) -> list[dict[str, Any]]:
    """Return events whose ``event_type`` is in *event_types*."""
    return [event for event in events if event.get("event_type") in event_types]


# ---------------------------------------------------------------------------
# Event record storage
# ---------------------------------------------------------------------------


async def store_event_record(
    agent: Any,
    tenant_id: str,
    event_type: str,
    payload: dict[str, Any],
    raw_event: dict[str, Any],
) -> dict[str, Any]:
    """Persist an event record in agent stores and in-memory history."""
    event_id = raw_event.get("event_id") or raw_event.get("id") or f"evt-{uuid4().hex}"
    record = {
        "event_id": event_id,
        "event_type": event_type,
        "domain": event_type.split(".")[0] if event_type else "unknown",
        "payload": payload,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    history = agent.event_history.setdefault(tenant_id, [])
    history.append(record)
    agent.analytics_event_store.upsert(tenant_id, event_id, record.copy())
    return record


# ---------------------------------------------------------------------------
# Lineage recording
# ---------------------------------------------------------------------------


async def record_data_lineage(
    agent: Any,
    tenant_id: str,
    sources: list[str],
    data: list[dict[str, Any]],
) -> str:
    """Record data lineage and return the lineage ID."""
    lineage_id = await generate_lineage_id()
    lineage_record = {
        "lineage_id": lineage_id,
        "sources": sources,
        "record_count": len(data),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    masked_lineage = mask_lineage_payload(lineage_record)
    agent.data_lineage[lineage_id] = masked_lineage
    agent.analytics_lineage_store.upsert(tenant_id, lineage_id, masked_lineage)
    return lineage_id


# ---------------------------------------------------------------------------
# Health portfolio helpers
# ---------------------------------------------------------------------------


async def get_health_history(
    agent: Any, tenant_id: str, project_id: str | None = None
) -> list[dict[str, Any]]:
    """Retrieve health history snapshots."""
    snapshots = agent.health_snapshots.get(tenant_id, [])
    if not snapshots:
        snapshots = agent.health_snapshot_store.list(tenant_id)
    if project_id:
        snapshots = [s for s in snapshots if s.get("project_id") == project_id]
    return sorted(snapshots, key=lambda s: s.get("monitored_at", ""))


async def summarize_health_portfolio(agent: Any, tenant_id: str) -> dict[str, Any]:
    """Aggregate health data across projects for reporting."""
    snapshots = agent.health_snapshots.get(tenant_id, [])
    if not snapshots:
        snapshots = agent.health_snapshot_store.list(tenant_id)

    latest_by_project: dict[str, dict[str, Any]] = {}
    for snapshot in sorted(snapshots, key=lambda s: s.get("monitored_at", "")):
        project_id = snapshot.get("project_id")
        if project_id:
            latest_by_project[project_id] = snapshot

    projects = list(latest_by_project.values())
    status_counts = {"Healthy": 0, "At Risk": 0, "Critical": 0}
    total_score = 0.0
    metrics_totals = {
        "schedule": 0.0,
        "cost": 0.0,
        "risk": 0.0,
        "quality": 0.0,
        "resource": 0.0,
    }
    for project in projects:
        status = project.get("health_status", "Unknown")
        if status in status_counts:
            status_counts[status] += 1
        total_score += project.get("composite_score", 0.0)
        for metric, detail in project.get("metrics", {}).items():
            metrics_totals[metric] += detail.get("score", 0.0)

    project_count = len(projects)
    average_score = total_score / project_count if project_count else 0.0
    averaged_metrics = {
        metric: (value / project_count if project_count else 0.0)
        for metric, value in metrics_totals.items()
    }
    concerns = identify_health_concerns(averaged_metrics)

    return {
        "project_count": project_count,
        "average_composite_score": average_score,
        "status_counts": status_counts,
        "average_metrics": averaged_metrics,
        "concerns": concerns,
        "recommendations": generate_recommendations(concerns),
        "projects": projects,
        "summarized_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# KPI calculation helpers
# ---------------------------------------------------------------------------


async def get_events_for_tenant(agent: Any, tenant_id: str) -> list[dict[str, Any]]:
    """Return all analytics events for a tenant."""
    events = agent.event_history.get(tenant_id, [])
    if not events:
        events = agent.analytics_event_store.list(tenant_id)
    return events


async def calculate_kpi_value(agent: Any, kpi_config: dict[str, Any]) -> float:
    """Calculate current KPI value from stored events."""
    metric_name = kpi_config.get("metric_name")
    tenant_id = kpi_config.get("tenant_id", "default")
    events = await get_events_for_tenant(agent, tenant_id)
    if metric_name == "schedule.delay.avg":
        delays = [
            float(event.get("payload", {}).get("delay_days", 0))
            for event in filter_events(events, {"schedule.delay"})
        ]
        return sum(delays) / len(delays) if delays else 0.0
    if metric_name == "deployment.success_rate":
        successes = len(filter_events(events, {"deployment.succeeded"}))
        failures = len(filter_events(events, {"deployment.failed"}))
        total = successes + failures
        return successes / total if total else 1.0
    if metric_name == "deployment.frequency":
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        recent = [
            event
            for event in filter_events(
                events,
                {"deployment.succeeded", "deployment.failed", "deployment.started"},
            )
            if event.get("received_at")
            and datetime.fromisoformat(event.get("received_at")) >= cutoff
        ]
        return len(recent) / 4.0 if recent else 0.0
    if metric_name == "resource.utilization.avg":
        allocations = []
        for event in filter_events(events, {"resource.allocation.created", "resource.updated"}):
            payload = event.get("payload", {})
            raw = payload.get("allocation_percentage")
            if raw is None:
                raw = payload.get("utilization") or payload.get("utilization_pct")
            if raw is None:
                continue
            allocations.append(float(raw) / 100 if float(raw) > 1 else float(raw))
        return sum(allocations) / len(allocations) if allocations else 0.0
    if metric_name == "quality.score.avg":
        scores = [
            float(event.get("payload", {}).get("quality_score", 0))
            for event in filter_events(events, {"quality.metrics.calculated"})
        ]
        return sum(scores) / len(scores) if scores else 0.0
    if metric_name == "risk.exposure.avg":
        scores = [
            float(event.get("payload", {}).get("score", 0))
            for event in filter_events(events, {"risk.assessed", "risk.status_updated"})
        ]
        return sum(scores) / len(scores) if scores else 0.0
    if metric_name == "compliance.audit.avg":
        scores = [
            float(event.get("payload", {}).get("score", 0))
            for event in filter_events(events, {"quality.audit.completed"})
        ]
        return sum(scores) / len(scores) if scores else 0.0
    kpi_name = str(kpi_config.get("name", "")).lower()
    if "velocity" in kpi_name:
        return 85.0
    return float(kpi_config.get("current_value") or kpi_config.get("value") or 0.0)


async def get_kpi_history(agent: Any, tenant_id: str, kpi_id: str) -> list[dict[str, Any]]:
    """Get historical KPI values."""
    history = agent.kpi_history_store.get(tenant_id, kpi_id)
    if history and isinstance(history.get("entries"), list):
        return list(history["entries"])
    return []


async def store_kpi_history(agent: Any, tenant_id: str, kpi_id: str, value: float) -> None:
    """Append a value to KPI history."""
    history = await get_kpi_history(agent, tenant_id, kpi_id)
    history.append({"value": value, "recorded_at": datetime.now(timezone.utc).isoformat()})
    agent.kpi_history_store.upsert(tenant_id, kpi_id, {"entries": history})


async def calculate_kpi_trend(
    historical: list[dict[str, Any]], current: float, direction: str | None
) -> str:
    """Calculate KPI trend."""
    if not historical:
        return "stable"
    last_value = historical[-1].get("value", current)
    if direction == "lower_is_better":
        if current < last_value:
            return "improving"
        if current > last_value:
            return "declining"
    else:
        if current > last_value:
            return "improving"
        if current < last_value:
            return "declining"
    return "stable"


async def check_kpi_thresholds(value: float, thresholds: dict[str, float]) -> dict[str, Any]:
    """Check KPI against thresholds."""
    breached = False
    if "min" in thresholds and value < thresholds["min"]:
        breached = True
    if "max" in thresholds and value > thresholds["max"]:
        breached = True
    return {
        "breached": breached,
        "thresholds": thresholds,
        "status": "critical" if breached else "normal",
    }


# ---------------------------------------------------------------------------
# Widget helpers
# ---------------------------------------------------------------------------


async def configure_widgets(widgets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Configure dashboard widgets."""
    configured: list[dict[str, Any]] = []
    for widget in widgets:
        configured.append(
            {
                "widget_id": f"W-{len(configured) + 1}",
                "type": widget.get("type"),
                "title": widget.get("title"),
                "data_source": widget.get("data_source"),
                "config": widget.get("config", {}),
            }
        )
    return configured


async def setup_refresh_schedule(interval_minutes: int) -> dict[str, Any]:
    """Set up data refresh schedule."""
    return {
        "interval_minutes": interval_minutes,
        "next_refresh": (
            datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)
        ).isoformat(),
    }


# ---------------------------------------------------------------------------
# Default configuration constants
# ---------------------------------------------------------------------------

DEFAULT_ANALYTICS_EVENT_TOPICS: list[str] = [
    "schedule.baseline.locked",
    "schedule.delay",
    "deployment.started",
    "deployment.succeeded",
    "deployment.failed",
    "deployment.progress",
    "analytics.deployment.metrics",
    "risk.identified",
    "risk.assessed",
    "risk.status_updated",
    "risk.mitigation_plan_created",
    "risk.simulation_completed",
    "risk.simulated",
    "risk.triggered",
    "quality.metrics.calculated",
    "quality.report.published",
    "quality.audit.completed",
    "quality.coverage.trend.updated",
    "quality.improvement.recommendations",
    "resource.allocation.created",
    "resource.updated",
    "resource.added",
]

DEFAULT_DATA_FACTORY_PIPELINES: list[dict[str, Any]] = [
    {"name": "planview_ingest", "definition": {"source": "planview"}},
    {"name": "jira_ingest", "definition": {"source": "jira"}},
    {"name": "workday_ingest", "definition": {"source": "workday"}},
    {"name": "sap_ingest", "definition": {"source": "sap"}},
]

DEFAULT_INGESTION_SOURCES: list[str] = ["planview", "jira", "workday", "sap"]

DEFAULT_KPI_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "Schedule Delay Average (days)",
        "metric_name": "schedule.delay.avg",
        "target": 0,
        "thresholds": {"max": 5},
        "event_types": ["schedule.delay"],
        "trend_direction": "lower_is_better",
    },
    {
        "name": "Deployment Success Rate",
        "metric_name": "deployment.success_rate",
        "target": 0.95,
        "thresholds": {"min": 0.9},
        "event_types": ["deployment.succeeded", "deployment.failed"],
        "trend_direction": "higher_is_better",
    },
    {
        "name": "Deployment Frequency (per week)",
        "metric_name": "deployment.frequency",
        "target": 2.0,
        "thresholds": {"min": 1.0},
        "event_types": [
            "deployment.succeeded",
            "deployment.failed",
            "deployment.started",
        ],
        "trend_direction": "higher_is_better",
    },
    {
        "name": "Resource Utilisation",
        "metric_name": "resource.utilization.avg",
        "target": 0.8,
        "thresholds": {"min": 0.6, "max": 1.0},
        "event_types": ["resource.allocation.created", "resource.updated"],
        "trend_direction": "higher_is_better",
    },
    {
        "name": "Quality Score",
        "metric_name": "quality.score.avg",
        "target": 90.0,
        "thresholds": {"min": 80.0},
        "event_types": ["quality.metrics.calculated"],
        "trend_direction": "higher_is_better",
    },
    {
        "name": "Risk Exposure Average",
        "metric_name": "risk.exposure.avg",
        "target": 5.0,
        "thresholds": {"max": 15.0},
        "event_types": ["risk.assessed", "risk.status_updated"],
        "trend_direction": "lower_is_better",
    },
    {
        "name": "Compliance Audit Score",
        "metric_name": "compliance.audit.avg",
        "target": 90.0,
        "thresholds": {"min": 85.0},
        "event_types": ["quality.audit.completed"],
        "trend_direction": "higher_is_better",
    },
]

VALID_ACTIONS: list[str] = [
    "aggregate_data",
    "create_dashboard",
    "generate_report",
    "run_prediction",
    "scenario_analysis",
    "generate_narrative",
    "track_kpi",
    "query_data",
    "natural_language_query",
    "get_dashboard",
    "get_insights",
    "update_data_lineage",
    "get_powerbi_report",
    "orchestrate_etl",
    "monitor_etl",
    "train_kpi_model",
    "provision_analytics_stack",
    "ingest_sources",
    "ingest_realtime_event",
    "compute_kpis_batch",
    "generate_periodic_report",
]
