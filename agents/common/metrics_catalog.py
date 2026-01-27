"""Central catalog for project health and performance metrics."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable

MetricExtractor = Callable[[dict[str, Any]], float | None]
MetricRequestBuilder = Callable[[str, dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class MetricDefinition:
    """Definition of a project health metric and its data source."""

    name: str
    description: str
    source_agent: str
    action: str
    request_builder: MetricRequestBuilder
    extractor: MetricExtractor
    unit: str


def _schedule_request_builder(project_id: str, context: dict[str, Any]) -> dict[str, Any]:
    schedule_id = context.get("schedule_id") or project_id
    tenant_id = context.get("tenant_id", "default")
    correlation_id = context.get("correlation_id", "metric-calc")
    return {
        "action": "track_variance",
        "schedule_id": schedule_id,
        "tenant_id": tenant_id,
        "correlation_id": correlation_id,
    }


def _cost_request_builder(project_id: str, context: dict[str, Any]) -> dict[str, Any]:
    tenant_id = context.get("tenant_id", "default")
    return {
        "action": "analyze_variance",
        "project_id": project_id,
        "tenant_id": tenant_id,
    }


def _risk_request_builder(project_id: str, context: dict[str, Any]) -> dict[str, Any]:
    tenant_id = context.get("tenant_id", "default")
    return {
        "action": "get_risk_dashboard",
        "project_id": project_id,
        "tenant_id": tenant_id,
    }


def _quality_request_builder(project_id: str, context: dict[str, Any]) -> dict[str, Any]:
    tenant_id = context.get("tenant_id", "default")
    return {
        "action": "calculate_metrics",
        "project_id": project_id,
        "tenant_id": tenant_id,
    }


def _resource_request_builder(project_id: str, context: dict[str, Any]) -> dict[str, Any]:
    tenant_id = context.get("tenant_id", "default")
    filters = {"project_id": project_id}
    filters.update(context.get("resource_filters", {}))
    return {
        "action": "get_utilization",
        "filters": filters,
        "tenant_id": tenant_id,
    }


def _extract_schedule_variance(response: dict[str, Any]) -> float | None:
    return response.get("schedule_variance_pct")


def _extract_cost_variance(response: dict[str, Any]) -> float | None:
    return response.get("budget_variance_pct")


def _extract_risk_score(response: dict[str, Any]) -> float | None:
    summary = response.get("risk_summary", {})
    total = summary.get("total_risks", 0)
    high = summary.get("high_risks", 0)
    if total <= 0:
        return 0.0
    return high / total


def _extract_quality_score(response: dict[str, Any]) -> float | None:
    return response.get("quality_score")


def _extract_resource_utilization(response: dict[str, Any]) -> float | None:
    return response.get("average_utilization")


METRIC_DEFINITIONS: dict[str, MetricDefinition] = {
    "schedule_variance": MetricDefinition(
        name="schedule_variance",
        description="Schedule variance percentage relative to baseline",
        source_agent="schedule",
        action="track_variance",
        request_builder=_schedule_request_builder,
        extractor=_extract_schedule_variance,
        unit="percentage",
    ),
    "cost_variance": MetricDefinition(
        name="cost_variance",
        description="Budget variance percentage relative to baseline",
        source_agent="financial",
        action="analyze_variance",
        request_builder=_cost_request_builder,
        extractor=_extract_cost_variance,
        unit="percentage",
    ),
    "risk_score": MetricDefinition(
        name="risk_score",
        description="Risk exposure score derived from risk dashboard",
        source_agent="risk",
        action="get_risk_dashboard",
        request_builder=_risk_request_builder,
        extractor=_extract_risk_score,
        unit="ratio",
    ),
    "quality_score": MetricDefinition(
        name="quality_score",
        description="Quality score from QA metrics",
        source_agent="quality",
        action="calculate_metrics",
        request_builder=_quality_request_builder,
        extractor=_extract_quality_score,
        unit="score",
    ),
    "resource_utilization": MetricDefinition(
        name="resource_utilization",
        description="Average resource utilization across the team",
        source_agent="resource",
        action="get_utilization",
        request_builder=_resource_request_builder,
        extractor=_extract_resource_utilization,
        unit="ratio",
    ),
}


def normalize_metric_value(metric_name: str, value: float | None) -> float:
    """Normalize raw metric values into a 0-1 health score."""
    if value is None:
        return 0.0

    if metric_name in {"schedule_variance", "cost_variance"}:
        return max(0.0, min(1.0, 1.0 - abs(float(value))))

    if metric_name == "risk_score":
        risk_value = float(value)
        if risk_value <= 1.0:
            return max(0.0, min(1.0, 1.0 - risk_value))
        return max(0.0, min(1.0, 1.0 - (risk_value / 25.0)))

    if metric_name == "quality_score":
        quality_value = float(value)
        if quality_value > 1.0:
            quality_value = quality_value / 100.0
        return max(0.0, min(1.0, quality_value))

    if metric_name == "resource_utilization":
        utilization = max(0.0, min(float(value), 1.5))
        if utilization < 0.75:
            score = utilization / 0.75
        elif utilization > 0.9:
            score = max(0.0, 1 - ((utilization - 0.9) / 0.2))
        else:
            score = 1.0
        return max(0.0, min(score, 1.0))

    return max(0.0, min(float(value), 1.0))


def _fallback_metric(metric_name: str, fallback: dict[str, Any]) -> float | None:
    if metric_name == "schedule_variance":
        schedule = fallback.get("schedule", {})
        return schedule.get("variance_pct")
    if metric_name == "cost_variance":
        cost = fallback.get("cost", {})
        return cost.get("variance_pct")
    if metric_name == "risk_score":
        risk = fallback.get("risk", {})
        return risk.get("risk_score")
    if metric_name == "quality_score":
        quality = fallback.get("quality", {})
        return quality.get("quality_score") or quality.get("test_pass_rate")
    if metric_name == "resource_utilization":
        resource = fallback.get("resource", {})
        utilization = resource.get("utilization")
        if utilization is None:
            utilization_pct = resource.get("utilization_pct")
            if utilization_pct is not None:
                return float(utilization_pct) / 100
        return utilization
    return None


def get_metric_definition(metric_name: str) -> MetricDefinition:
    """Return the metric definition for the given name."""
    if metric_name not in METRIC_DEFINITIONS:
        raise ValueError(f"Unknown metric: {metric_name}")
    return METRIC_DEFINITIONS[metric_name]


async def get_metric_value(
    metric_name: str,
    project_id: str,
    *,
    tenant_id: str,
    context: dict[str, Any] | None = None,
    agent_clients: dict[str, Any] | None = None,
    fallback: dict[str, Any] | None = None,
) -> float | None:
    """Fetch a metric value by routing to the configured source agent."""
    definition = get_metric_definition(metric_name)
    context = context or {}
    context.setdefault("tenant_id", tenant_id)

    agent_client = agent_clients.get(definition.source_agent) if agent_clients else None
    if agent_client:
        request = definition.request_builder(project_id, context)
        response = agent_client.process(request)
        if inspect.isawaitable(response):
            response = await response
        value = definition.extractor(response)
        if value is not None:
            return float(value)

    if fallback:
        return _fallback_metric(metric_name, fallback)

    return None
