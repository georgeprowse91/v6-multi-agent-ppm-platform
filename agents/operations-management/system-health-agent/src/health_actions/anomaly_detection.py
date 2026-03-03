"""Action handlers for anomaly detection."""

from __future__ import annotations

import asyncio
import statistics
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from health_utils import recommend_actions_for_anomaly, generate_anomaly_id

if TYPE_CHECKING:
    from system_health_agent import SystemHealthAgent

# ---------------------------------------------------------------------------
# Lazy Azure imports
# ---------------------------------------------------------------------------
import importlib.util


def _safe_find_spec(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ModuleNotFoundError, ValueError):
        return False


_HAS_AZURE = _safe_find_spec("azure")
_HAS_ANOMALY_DETECTOR = _HAS_AZURE and (_safe_find_spec("azure.ai.anomalydetector"))
if _HAS_ANOMALY_DETECTOR:
    from azure.ai.anomalydetector import AnomalyDetectorClient
    from azure.ai.anomalydetector.models import TimeSeriesPoint
    from azure.core.credentials import AzureKeyCredential
else:
    AnomalyDetectorClient = None  # type: ignore[assignment,misc]
    TimeSeriesPoint = None  # type: ignore[assignment,misc]
    AzureKeyCredential = None  # type: ignore[assignment,misc]


async def detect_anomalies(
    agent: SystemHealthAgent, tenant_id: str, service_name: str, time_range: dict[str, Any]
) -> dict[str, Any]:
    """Detect anomalies in service metrics.  Returns detected anomalies."""
    agent.logger.info("Detecting anomalies for service: %s", service_name)

    metrics = await agent._get_service_metrics(service_name, time_range)

    anomalies = await apply_anomaly_detection(agent, metrics)

    for anomaly in anomalies:
        anomaly["recommended_actions"] = recommend_actions_for_anomaly(anomaly)
        anomaly_id = await generate_anomaly_id()
        agent.anomalies[anomaly_id] = {
            "anomaly_id": anomaly_id,
            "service_name": service_name,
            "metric_name": anomaly.get("metric"),
            "value": anomaly.get("value"),
            "expected_range": anomaly.get("expected_range"),
            "severity": anomaly.get("severity"),
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }
        if anomaly.get("severity") == "critical":
            await create_servicenow_incident(
                agent,
                {
                    "title": f"{service_name} anomaly detected",
                    "description": f"{anomaly.get('metric')} value {anomaly.get('value')}",
                    "severity": "critical",
                    "affected_services": [service_name],
                },
            )
            # Import here to avoid circular dependency at module level
            from health_actions.alert_management import create_alert

            await create_alert(
                agent,
                tenant_id,
                {
                    "name": f"{service_name} anomaly detected",
                    "description": f"{anomaly.get('metric')} anomaly detected",
                    "severity": "critical",
                    "service_name": service_name,
                    "condition": "anomaly",
                    "threshold": anomaly.get("expected_range"),
                },
            )

    if anomalies:
        await emit_event_hub_event(
            agent,
            {
                "event_name": "system_health.alert",
                "type": "system_health.alert",
                "service_name": service_name,
                "time_range": time_range,
                "anomalies": anomalies,
                "recommended_actions": [
                    action
                    for anomaly in anomalies
                    for action in anomaly.get("recommended_actions", [])
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    return {
        "service_name": service_name,
        "anomalies_detected": len(anomalies),
        "anomalies": anomalies,
        "time_range": time_range,
    }


async def apply_anomaly_detection(
    agent: SystemHealthAgent, metrics: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Apply anomaly detection to metrics."""
    if not metrics:
        return []

    normalized: list[dict[str, Any]] = []
    for metric in metrics:
        if isinstance(metric.get("metrics"), dict):
            for name, value in metric["metrics"].items():
                normalized.append(
                    {
                        "metric": name,
                        "value": value,
                        "timestamp": metric.get("timestamp"),
                    }
                )
        else:
            normalized.append(metric)

    if _HAS_ANOMALY_DETECTOR and agent.anomaly_detector_endpoint and agent.anomaly_detector_key:
        return await _apply_azure_anomaly_detection(agent, normalized)

    anomalies: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for metric in normalized:
        name = metric.get("metric") or metric.get("metric_name") or "unknown"
        grouped.setdefault(name, []).append(metric)

    for name, points in grouped.items():
        values = [float(p.get("value", 0)) for p in points if p.get("value") is not None]
        if len(values) < 5:
            continue
        median = statistics.median(values)
        mad = statistics.median([abs(v - median) for v in values]) or 1.0
        for point in points:
            value = float(point.get("value", 0))
            modified_z = 0.6745 * (value - median) / mad
            if abs(modified_z) >= 3.5:
                anomalies.append(
                    {
                        "metric": name,
                        "value": value,
                        "expected_range": [median - 3 * mad, median + 3 * mad],
                        "severity": "critical" if abs(modified_z) >= 4.5 else "warning",
                        "timestamp": point.get("timestamp"),
                        "z_score": modified_z,
                    }
                )
    return anomalies


async def _apply_azure_anomaly_detection(
    agent: SystemHealthAgent, metrics: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not (agent.anomaly_detector_endpoint and agent.anomaly_detector_key):
        return []
    client = AnomalyDetectorClient(
        agent.anomaly_detector_endpoint, AzureKeyCredential(agent.anomaly_detector_key)
    )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for metric in metrics:
        name = metric.get("metric") or metric.get("metric_name") or "unknown"
        grouped.setdefault(name, []).append(metric)
    anomalies: list[dict[str, Any]] = []
    for name, points in grouped.items():
        series = [
            TimeSeriesPoint(
                timestamp=(
                    datetime.fromisoformat(p["timestamp"])
                    if isinstance(p.get("timestamp"), str)
                    else p.get("timestamp")
                ),
                value=p.get("value"),
            )
            for p in points
            if p.get("timestamp") and p.get("value") is not None
        ]
        if len(series) < 12:
            continue
        result = await asyncio.to_thread(client.detect_last_point, series=series)
        if result.is_anomaly:
            anomalies.append(
                {
                    "metric": name,
                    "value": series[-1].value,
                    "expected_range": [result.expected_value_low, result.expected_value_high],
                    "severity": "critical" if result.is_anomaly else "warning",
                    "timestamp": series[-1].timestamp,
                }
            )
    return anomalies
