"""Action handlers for dashboards, reporting, and metric queries."""

from __future__ import annotations

import statistics
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from health_utils import (
    extract_metric_series,
    extract_service_names,
    parse_time_range,
    summarize_service_metrics,
)

if TYPE_CHECKING:
    from system_health_agent import SystemHealthAgent


async def get_metrics(
    agent: SystemHealthAgent,
    service_name: str,
    metric_name: str,
    time_range: dict[str, Any],
) -> dict[str, Any]:
    """Get metric values for time range.  Returns metric data."""
    agent.logger.info("Getting metrics: %s.%s", service_name, metric_name)

    metric_values = await agent._query_metrics(service_name, metric_name, time_range)

    return {
        "service_name": service_name,
        "metric_name": metric_name,
        "time_range": time_range,
        "values": metric_values,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_deployment_metrics(
    agent: SystemHealthAgent, deployment_plan: dict[str, Any]
) -> dict[str, Any]:
    """Aggregate deployment metrics for release readiness checks."""
    service_names = extract_service_names(deployment_plan, agent.health_endpoints)
    time_range = deployment_plan.get("time_range", {"hours": 1})
    service_summaries: dict[str, dict[str, Any]] = {}
    overall: dict[str, list[float]] = {}

    for svc_name in service_names:
        records = await agent._get_service_metrics(svc_name, time_range)
        summary = summarize_service_metrics(records)
        service_summaries[svc_name] = summary
        for key, value in summary.items():
            if isinstance(value, (int, float)):
                overall.setdefault(key, []).append(float(value))

    aggregate = {key: statistics.mean(values) if values else 0.0 for key, values in overall.items()}

    return {
        "metrics": aggregate,
        "services": service_summaries,
        "time_range": time_range,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_deployment_baseline(
    agent: SystemHealthAgent, deployment_plan: dict[str, Any]
) -> dict[str, Any]:
    """Provide baseline metrics for deployment comparisons."""
    service_names = extract_service_names(deployment_plan, agent.health_endpoints)
    time_range = deployment_plan.get("baseline_time_range", {"days": 7})
    metric_baselines: dict[str, list[float]] = {"response_time_ms": [], "error_rate": []}

    for svc_name in service_names:
        records = await agent._get_service_metrics(svc_name, time_range)
        for metric_name in metric_baselines:
            metric_baselines[metric_name].extend(extract_metric_series(records, metric_name))

    baseline: dict[str, Any] = {}
    for metric_name, values in metric_baselines.items():
        if not values:
            continue
        baseline[metric_name] = {
            "mean": statistics.mean(values),
            "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
        }

    return baseline


async def query_historical_metrics(
    agent: SystemHealthAgent,
    service_name: str,
    metric_name: str,
    time_range: dict[str, Any],
) -> dict[str, Any]:
    values = await agent._query_metrics(service_name, metric_name, time_range)
    return {
        "service_name": service_name,
        "metric_name": metric_name,
        "time_range": time_range,
        "values": values,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_health_dashboard(
    agent: SystemHealthAgent, tenant_id: str, time_range: dict[str, Any]
) -> dict[str, Any]:
    """Generate health dashboard data with real-time and historical metrics."""
    from health_actions.check_health import get_system_status

    system_status = await get_system_status(agent)
    metrics_summary = summarize_metrics_history(agent, time_range, tenant_id=tenant_id)
    incident_summary = summarize_incidents(agent, tenant_id, time_range)
    alert_summary = summarize_alerts(agent, tenant_id, time_range)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "real_time": system_status,
        "historical_metrics": metrics_summary,
        "incident_summary": incident_summary,
        "alert_summary": alert_summary,
    }


async def get_postmortem_report(
    agent: SystemHealthAgent, tenant_id: str, time_range: dict[str, Any]
) -> dict[str, Any]:
    """Summarize incidents and response times for postmortem analysis."""
    incident_summary = summarize_incidents(agent, tenant_id, time_range)
    alert_summary = summarize_alerts(agent, tenant_id, time_range)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "incident_summary": incident_summary,
        "alert_summary": alert_summary,
        "time_range": time_range,
    }


async def get_grafana_dashboard(agent: SystemHealthAgent) -> dict[str, Any]:
    return {
        "folder": agent.grafana_folder,
        "dashboard": build_grafana_dashboard(agent),
    }


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------


def summarize_metrics_history(
    agent: SystemHealthAgent, time_range: dict[str, Any], tenant_id: str | None = None
) -> dict[str, Any]:
    start_time, end_time = parse_time_range(time_range)
    summaries: dict[str, dict[str, list[float]]] = {}
    total_records = 0

    for record in agent.metrics.values():
        if tenant_id and record.get("tenant_id") != tenant_id:
            continue
        timestamp = record.get("timestamp")
        if timestamp:
            parsed = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp
            if parsed < start_time or parsed > end_time:
                continue
        total_records += 1
        svc_name = record.get("service_name", "unknown")
        metrics_data = record.get("metrics", {})
        if not isinstance(metrics_data, dict):
            continue
        for metric_name, value in metrics_data.items():
            if isinstance(value, (int, float)):
                summaries.setdefault(svc_name, {}).setdefault(metric_name, []).append(float(value))

    summarized: dict[str, dict[str, float]] = {}
    for svc_name, metrics in summaries.items():
        summarized[svc_name] = {
            name: statistics.mean(values) for name, values in metrics.items() if values
        }

    return {"total_records": total_records, "services": summarized}


def summarize_incidents(
    agent: SystemHealthAgent, tenant_id: str, time_range: dict[str, Any]
) -> dict[str, Any]:
    start_time, end_time = parse_time_range(time_range)
    incidents = agent.incident_store.list(tenant_id)
    filtered: list[dict[str, Any]] = []
    resolution_times: list[float] = []

    for incident in incidents:
        created_at = incident.get("created_at")
        created_dt = datetime.fromisoformat(created_at) if created_at else None
        if created_dt and (created_dt < start_time or created_dt > end_time):
            continue
        filtered.append(incident)
        resolved_at = incident.get("resolved_at")
        if resolved_at and created_dt:
            resolved_dt = datetime.fromisoformat(resolved_at)
            resolution_times.append((resolved_dt - created_dt).total_seconds() / 60)

    severity_counts: dict[str, int] = {}
    for incident in filtered:
        severity = incident.get("severity", "unknown")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    return {
        "total_incidents": len(filtered),
        "severity_counts": severity_counts,
        "average_resolution_minutes": (
            statistics.mean(resolution_times) if resolution_times else 0.0
        ),
    }


def summarize_alerts(
    agent: SystemHealthAgent, tenant_id: str, time_range: dict[str, Any]
) -> dict[str, Any]:
    start_time, end_time = parse_time_range(time_range)
    alerts = agent.alert_store.list(tenant_id)
    filtered: list[dict[str, Any]] = []
    response_times: list[float] = []

    for alert in alerts:
        created_at = alert.get("created_at")
        created_dt = datetime.fromisoformat(created_at) if created_at else None
        if created_dt and (created_dt < start_time or created_dt > end_time):
            continue
        filtered.append(alert)
        acknowledged_at = alert.get("acknowledged_at")
        if acknowledged_at and created_dt:
            ack_dt = datetime.fromisoformat(acknowledged_at)
            response_times.append((ack_dt - created_dt).total_seconds() / 60)

    severity_counts: dict[str, int] = {}
    for alert in filtered:
        severity = alert.get("severity", "unknown")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    return {
        "total_alerts": len(filtered),
        "severity_counts": severity_counts,
        "average_response_minutes": (statistics.mean(response_times) if response_times else 0.0),
    }


def build_grafana_dashboard(agent: SystemHealthAgent) -> dict[str, Any]:
    return {
        "title": "System Health Overview",
        "tags": ["system-health", "ops"],
        "timezone": "browser",
        "schemaVersion": 39,
        "version": 1,
        "refresh": "30s",
        "panels": [
            {
                "type": "stat",
                "title": "Service Health",
                "datasource": agent.grafana_datasource,
                "targets": [
                    {
                        "expr": "service_health_status",
                        "legendFormat": "{{service}}",
                    }
                ],
            },
            {
                "type": "timeseries",
                "title": "CPU Usage",
                "datasource": agent.grafana_datasource,
                "targets": [
                    {
                        "expr": "cpu_usage",
                        "legendFormat": "{{service}}",
                    }
                ],
            },
            {
                "type": "timeseries",
                "title": "Memory Usage",
                "datasource": agent.grafana_datasource,
                "targets": [
                    {
                        "expr": "memory_usage",
                        "legendFormat": "{{service}}",
                    }
                ],
            },
            {
                "type": "timeseries",
                "title": "Request Latency (ms)",
                "datasource": agent.grafana_datasource,
                "targets": [
                    {
                        "expr": "request_latency_ms",
                        "legendFormat": "{{service}}",
                    }
                ],
            },
            {
                "type": "timeseries",
                "title": "Error Rate",
                "datasource": agent.grafana_datasource,
                "targets": [
                    {
                        "expr": "error_rate",
                        "legendFormat": "{{service}}",
                    }
                ],
            },
        ],
    }
