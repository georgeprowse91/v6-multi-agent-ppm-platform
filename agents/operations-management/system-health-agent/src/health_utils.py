"""
Utility functions for the System Health & Monitoring Agent.

Shared helpers for ID generation, text sanitization, time parsing,
trend analysis, metric extraction, and Prometheus metric parsing.
"""

import json
import os
import re
import statistics
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

# ---------------------------------------------------------------------------
# PII sanitization
# ---------------------------------------------------------------------------

PII_PATTERNS = {
    "email": re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"\+?\d[\d\s().-]{7,}\d"),
}


def sanitize_text(value: str) -> str:
    """Redact PII-like patterns from loggable strings."""
    if not value:
        return value
    sanitized = value
    for pattern in PII_PATTERNS.values():
        sanitized = pattern.sub("[redacted]", sanitized)
    return sanitized


# ---------------------------------------------------------------------------
# ID generators
# ---------------------------------------------------------------------------


async def generate_metric_id() -> str:
    """Generate unique metric ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"METRIC-{timestamp}"


async def generate_alert_id() -> str:
    """Generate unique alert ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    return f"ALERT-{timestamp}-{suffix}"


async def generate_incident_id() -> str:
    """Generate unique incident ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"INC-{timestamp}"


async def generate_anomaly_id() -> str:
    """Generate unique anomaly ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"ANOM-{timestamp}"


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------


def parse_time_range(time_range: dict[str, Any]) -> tuple[datetime, datetime]:
    """Parse a time-range dict into (start, end) UTC datetimes."""
    end = datetime.now(timezone.utc)
    if "end" in time_range:
        end = datetime.fromisoformat(time_range["end"])
    if "start" in time_range:
        start = datetime.fromisoformat(time_range["start"])
    else:
        if "hours" in time_range:
            start = end - timedelta(hours=int(time_range.get("hours", 1)))
        elif "minutes" in time_range:
            start = end - timedelta(minutes=int(time_range.get("minutes", 60)))
        else:
            days = int(time_range.get("days", 1))
            start = end - timedelta(days=days)
    return start, end


# ---------------------------------------------------------------------------
# Trend / forecast helpers
# ---------------------------------------------------------------------------


def summarize_trend(values: list[dict[str, Any]]) -> dict[str, Any]:
    series = [
        {"timestamp": v.get("timestamp"), "value": float(v.get("value", 0))}
        for v in values
        if v.get("value") is not None
    ]
    if len(series) < 2:
        return {"direction": "stable", "series": series}
    first = series[0]["value"]
    last = series[-1]["value"]
    if last > first * 1.05:
        direction = "increasing"
    elif last < first * 0.95:
        direction = "decreasing"
    else:
        direction = "stable"
    return {"direction": direction, "series": series}


def linear_regression_forecast(series: list[dict[str, Any]], horizon_days: int) -> float | None:
    if len(series) < 2:
        return None
    x_values = list(range(len(series)))
    y_values = [point["value"] for point in series]
    x_mean = statistics.mean(x_values)
    y_mean = statistics.mean(y_values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    denominator = sum((x - x_mean) ** 2 for x in x_values) or 1
    slope = numerator / denominator
    forecast_index = len(series) - 1 + horizon_days
    forecast = y_mean + slope * (forecast_index - x_mean)
    return round(forecast, 2)


# ---------------------------------------------------------------------------
# Metric extraction / summarization helpers
# ---------------------------------------------------------------------------


def extract_service_names(
    deployment_plan: dict[str, Any], health_endpoints: list[dict[str, Any]]
) -> list[str]:
    service_names = deployment_plan.get("services") or deployment_plan.get("service_names")
    if isinstance(service_names, list) and service_names:
        return [str(name) for name in service_names]
    if deployment_plan.get("service_name"):
        return [str(deployment_plan["service_name"])]
    return [
        endpoint.get("name") or endpoint.get("service")
        for endpoint in health_endpoints
        if endpoint.get("name") or endpoint.get("service")
    ] or ["platform"]


def extract_metric_series(records: list[dict[str, Any]], metric_name: str) -> list[float]:
    values: list[float] = []
    for record in records:
        if isinstance(record.get("metrics"), dict):
            value = record["metrics"].get(metric_name)
        elif record.get("metric") == metric_name:
            value = record.get("value")
        else:
            value = None
        if value is None:
            continue
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            continue
    return values


def summarize_service_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for metric_name in [
        "response_time_ms",
        "error_rate",
        "cpu_usage",
        "memory_usage",
        "disk_usage",
    ]:
        values = extract_metric_series(records, metric_name)
        if values:
            summary[metric_name] = statistics.mean(values)
    return summary


def recommend_actions_for_anomaly(anomaly: dict[str, Any]) -> list[str]:
    metric = anomaly.get("metric", "")
    recommendations: list[str] = []
    if "error" in metric:
        recommendations.extend(
            [
                "Inspect recent deployments for regressions.",
                "Review service logs for failing requests.",
            ]
        )
    if "response" in metric or "latency" in metric:
        recommendations.extend(
            [
                "Check downstream dependency latency.",
                "Scale service instances or increase resources.",
            ]
        )
    if "cpu" in metric:
        recommendations.append("Scale CPU resources or rebalance workloads.")
    if "memory" in metric:
        recommendations.append("Increase memory allocation or investigate leaks.")
    if "disk" in metric:
        recommendations.append("Clear disk space or expand storage.")
    if "network" in metric:
        recommendations.append("Inspect network throughput and packet loss.")
    if not recommendations:
        recommendations.append("Investigate recent changes and correlated metrics.")
    return recommendations


# ---------------------------------------------------------------------------
# Prometheus text format parser
# ---------------------------------------------------------------------------

_PROM_LINE_PATTERN = re.compile(
    r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s+(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)$"
)


def parse_prometheus_metrics(payload: str) -> dict[str, Any]:
    cpu_totals: dict[str, float] = {}
    cpu_idle: dict[str, float] = {}
    mem_total = None
    mem_available = None
    disk_totals: dict[str, float] = {}
    disk_avail: dict[str, float] = {}
    net_rx_total = 0.0
    net_tx_total = 0.0

    for line in payload.splitlines():
        if not line or line.startswith("#"):
            continue
        match = _PROM_LINE_PATTERN.match(line.strip())
        if not match:
            continue
        name, labels_raw, value_raw = match.groups()
        try:
            value = float(value_raw)
        except ValueError:
            continue
        labels: dict[str, str] = {}
        if labels_raw:
            label_pairs = labels_raw.strip("{}").split(",")
            for pair in label_pairs:
                if "=" not in pair:
                    continue
                key, raw_value = pair.split("=", 1)
                labels[key.strip()] = raw_value.strip().strip('"')

        if name == "node_cpu_seconds_total":
            cpu = labels.get("cpu", "all")
            cpu_totals[cpu] = cpu_totals.get(cpu, 0.0) + value
            if labels.get("mode") == "idle":
                cpu_idle[cpu] = cpu_idle.get(cpu, 0.0) + value
        elif name == "node_memory_MemTotal_bytes":
            mem_total = value
        elif name == "node_memory_MemAvailable_bytes":
            mem_available = value
        elif name == "node_filesystem_size_bytes":
            mount = labels.get("mountpoint", "root")
            fstype = labels.get("fstype", "")
            if fstype in {"tmpfs", "overlay", "squashfs", "proc", "sysfs"}:
                continue
            disk_totals[mount] = disk_totals.get(mount, 0.0) + value
        elif name == "node_filesystem_avail_bytes":
            mount = labels.get("mountpoint", "root")
            fstype = labels.get("fstype", "")
            if fstype in {"tmpfs", "overlay", "squashfs", "proc", "sysfs"}:
                continue
            disk_avail[mount] = disk_avail.get(mount, 0.0) + value
        elif name == "node_network_receive_bytes_total":
            if labels.get("device") == "lo":
                continue
            net_rx_total += value
        elif name == "node_network_transmit_bytes_total":
            if labels.get("device") == "lo":
                continue
            net_tx_total += value

    cpu_usage = None
    if cpu_totals:
        cpu_values = []
        for cpu, total in cpu_totals.items():
            idle = cpu_idle.get(cpu, 0.0)
            if total > 0:
                cpu_values.append(1 - (idle / total))
        if cpu_values:
            cpu_usage = statistics.mean(cpu_values)

    memory_usage = None
    if mem_total and mem_available is not None:
        memory_usage = (mem_total - mem_available) / mem_total

    disk_usage = None
    if disk_totals:
        usage_values = []
        for mount, total in disk_totals.items():
            avail = disk_avail.get(mount, 0.0)
            if total > 0:
                usage_values.append((total - avail) / total)
        if usage_values:
            disk_usage = statistics.mean(usage_values)

    return {
        "cpu_usage": cpu_usage,
        "memory_usage": memory_usage,
        "disk_usage": disk_usage,
        "network_rx_bytes_total": net_rx_total,
        "network_tx_bytes_total": net_tx_total,
    }


# ---------------------------------------------------------------------------
# Environment-variable loaders
# ---------------------------------------------------------------------------


def load_health_endpoints(logger: Any = None) -> list[dict[str, Any]]:
    raw = os.getenv("HEALTH_ENDPOINTS")
    if not raw:
        return []
    try:
        endpoints = json.loads(raw)
    except json.JSONDecodeError:
        if logger:
            logger.warning("Unable to parse HEALTH_ENDPOINTS JSON")
        return []
    if isinstance(endpoints, list):
        return endpoints
    return []


def load_prometheus_scrape_targets(logger: Any = None) -> list[dict[str, Any]]:
    raw = os.getenv("PROMETHEUS_SCRAPE_TARGETS")
    if not raw:
        return []
    try:
        targets = json.loads(raw)
    except json.JSONDecodeError:
        if logger:
            logger.warning("Unable to parse PROMETHEUS_SCRAPE_TARGETS JSON")
        return []
    if isinstance(targets, list):
        return targets
    return []


def load_monitor_resource_ids(logger: Any = None) -> list[dict[str, Any]]:
    raw = os.getenv("MONITOR_RESOURCE_IDS")
    if not raw:
        return []
    try:
        resources = json.loads(raw)
    except json.JSONDecodeError:
        if logger:
            logger.warning("Unable to parse MONITOR_RESOURCE_IDS JSON")
        return []
    if isinstance(resources, list):
        return resources
    return []
