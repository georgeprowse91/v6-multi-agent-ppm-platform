from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

import httpx
from metrics_store import MetricsStore

from agents.common.metrics_catalog import normalize_metric_value

logger = logging.getLogger("analytics-service.kpi")


@dataclass(frozen=True)
class KpiSnapshot:
    project_id: str
    tenant_id: str
    computed_at: datetime
    metrics: dict[str, float | None]
    normalized: dict[str, float]


@dataclass(frozen=True)
class KpiTrendPoint:
    timestamp: datetime
    value: float | None


@dataclass(frozen=True)
class KpiTrendSeries:
    metric: str
    points: list[KpiTrendPoint]
    slope: float | None
    forecast: float | None
    forecast_method: str | None
    recent_change: float | None


@dataclass(frozen=True)
class KpiTrendSnapshot:
    project_id: str
    tenant_id: str
    computed_at: datetime
    period_count: int
    series: list[KpiTrendSeries]


class AnalyticsDataClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self._client = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout)

    async def list_entities(
        self,
        schema_name: str,
        tenant_id: str,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        response = await self._client.get(
            f"/entities/{schema_name}",
            params={"tenant_id": tenant_id, "limit": limit},
            headers={"X-Tenant-ID": tenant_id},
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self._client.aclose()


class AnalyticsKpiEngine:
    def __init__(
        self, data_client: AnalyticsDataClient, metrics_store: MetricsStore | None
    ) -> None:
        self._data_client = data_client
        self._metrics_store = metrics_store

    async def compute_kpis(self, project_id: str, tenant_id: str) -> KpiSnapshot:
        work_items, budgets, risks, resources = await asyncio.gather(
            self._data_client.list_entities("work-item", tenant_id),
            self._data_client.list_entities("budget", tenant_id),
            self._data_client.list_entities("risk", tenant_id),
            self._data_client.list_entities("resource", tenant_id),
        )
        metrics = compute_kpis_from_entities(
            project_id=project_id,
            work_items=work_items,
            budgets=budgets,
            risks=risks,
            resources=resources,
        )
        normalized = {name: normalize_metric_value(name, value) for name, value in metrics.items()}
        snapshot = KpiSnapshot(
            project_id=project_id,
            tenant_id=tenant_id,
            computed_at=datetime.now(timezone.utc),
            metrics=metrics,
            normalized=normalized,
        )
        if self._metrics_store:
            self._metrics_store.add_snapshot(tenant_id, project_id, metrics, snapshot.computed_at)
        return snapshot


@dataclass(frozen=True)
class NarrativeReport:
    summary: str
    highlights: list[str]
    risks: list[str]
    opportunities: list[str]
    data_quality_notes: list[str]


def compute_kpis_from_entities(
    *,
    project_id: str,
    work_items: list[dict[str, Any]],
    budgets: list[dict[str, Any]],
    risks: list[dict[str, Any]],
    resources: list[dict[str, Any]],
) -> dict[str, float | None]:
    project_work_items = [
        item for item in work_items if _matches_project(item.get("data"), project_id)
    ]
    project_budgets = [item for item in budgets if _matches_project(item.get("data"), project_id)]
    project_risks = [item for item in risks if _matches_project(item.get("data"), project_id)]
    project_resources = [
        item for item in resources if _matches_project(item.get("data"), project_id)
    ]

    schedule_variance = _calculate_schedule_variance(project_work_items)
    cost_variance = _calculate_cost_variance(project_budgets)
    risk_score = _calculate_risk_score(project_risks)
    quality_score = _calculate_quality_score(project_work_items)
    resource_utilization = _calculate_resource_utilization(project_resources, project_work_items)

    return {
        "schedule_variance": schedule_variance,
        "cost_variance": cost_variance,
        "risk_score": risk_score,
        "quality_score": quality_score,
        "resource_utilization": resource_utilization,
    }


def generate_narrative(snapshot: KpiSnapshot) -> NarrativeReport:
    highlights: list[str] = []
    risks: list[str] = []
    opportunities: list[str] = []
    data_quality_notes: list[str] = []

    for metric_name, value in snapshot.metrics.items():
        if value is None:
            data_quality_notes.append(f"No data available for {metric_name}.")
            continue
        normalized = snapshot.normalized.get(metric_name, 0.0)
        if normalized >= 0.85:
            highlights.append(f"{metric_name.replace('_', ' ').title()} is strong ({value:.2f}).")
        elif normalized >= 0.7:
            opportunities.append(
                f"{metric_name.replace('_', ' ').title()} is moderate ({value:.2f})."
            )
        else:
            risks.append(f"{metric_name.replace('_', ' ').title()} needs attention ({value:.2f}).")

    summary = _build_summary(snapshot)
    return NarrativeReport(
        summary=summary,
        highlights=highlights,
        risks=risks,
        opportunities=opportunities,
        data_quality_notes=data_quality_notes,
    )


def apply_what_if_adjustments(snapshot: KpiSnapshot, adjustments: dict[str, Any]) -> KpiSnapshot:
    adjusted_metrics = dict(snapshot.metrics)
    for metric_name, raw_adjustment in adjustments.items():
        if metric_name not in adjusted_metrics:
            continue
        current = adjusted_metrics.get(metric_name)
        if current is None:
            current = 0.0
        value, mode = _parse_adjustment(raw_adjustment)
        if mode == "absolute":
            adjusted_metrics[metric_name] = value
        else:
            adjusted_metrics[metric_name] = current + value
    normalized = {
        name: normalize_metric_value(name, value) for name, value in adjusted_metrics.items()
    }
    return KpiSnapshot(
        project_id=snapshot.project_id,
        tenant_id=snapshot.tenant_id,
        computed_at=datetime.now(timezone.utc),
        metrics=adjusted_metrics,
        normalized=normalized,
    )


def compute_kpi_trends(
    *,
    project_id: str,
    tenant_id: str,
    snapshots: list[Any],
    metrics: list[str] | None = None,
    period_count: int = 6,
) -> KpiTrendSnapshot:
    selected_metrics = metrics or [
        "schedule_variance",
        "cost_variance",
        "risk_score",
        "quality_score",
        "resource_utilization",
    ]
    limited_snapshots = snapshots[-period_count:] if period_count > 0 else snapshots
    series_list: list[KpiTrendSeries] = []
    for metric_name in selected_metrics:
        points = [
            KpiTrendPoint(timestamp=snapshot.captured_at, value=snapshot.metrics.get(metric_name))
            for snapshot in limited_snapshots
        ]
        values = [point.value for point in points if point.value is not None]
        slope, forecast, method = _forecast_metric(values)
        recent_change = _compute_recent_change(values)
        series_list.append(
            KpiTrendSeries(
                metric=metric_name,
                points=points,
                slope=slope,
                forecast=forecast,
                forecast_method=method,
                recent_change=recent_change,
            )
        )
    return KpiTrendSnapshot(
        project_id=project_id,
        tenant_id=tenant_id,
        computed_at=datetime.now(timezone.utc),
        period_count=period_count,
        series=series_list,
    )


def _parse_adjustment(adjustment: Any) -> tuple[float, str]:
    if isinstance(adjustment, dict):
        value = float(adjustment.get("value", 0.0))
        mode = adjustment.get("mode", "delta")
        return value, str(mode)
    try:
        return float(adjustment), "delta"
    except (TypeError, ValueError):
        return 0.0, "delta"


def _calculate_schedule_variance(work_items: list[dict[str, Any]]) -> float | None:
    if not work_items:
        return None
    today = date.today()
    overdue = 0
    total = 0
    for item in work_items:
        data = item.get("data", {})
        due_date = _parse_date(data.get("due_date"))
        status = (data.get("status") or "").lower()
        if due_date:
            total += 1
            if due_date < today and status != "done":
                overdue += 1
    if total == 0:
        return 0.0
    return -1.0 * (overdue / total)


def _calculate_cost_variance(budgets: list[dict[str, Any]]) -> float | None:
    planned_total = 0.0
    actual_total = 0.0
    for item in budgets:
        data = item.get("data", {})
        planned = _coerce_float(data.get("amount"))
        actual = _extract_actual_cost(data)
        if planned is None or actual is None:
            continue
        planned_total += planned
        actual_total += actual
    if planned_total <= 0:
        return None
    return (actual_total - planned_total) / planned_total


def _calculate_risk_score(risks: list[dict[str, Any]]) -> float | None:
    if not risks:
        return None
    total = 0
    high = 0
    for item in risks:
        data = item.get("data", {})
        total += 1
        impact = (data.get("impact") or "").lower()
        likelihood = (data.get("likelihood") or "").lower()
        if impact in {"high", "critical"} or likelihood in {"likely"}:
            high += 1
    if total == 0:
        return None
    return high / total


def _calculate_quality_score(work_items: list[dict[str, Any]]) -> float | None:
    if not work_items:
        return None
    total = len(work_items)
    done = 0
    blocked = 0
    for item in work_items:
        status = (item.get("data", {}).get("status") or "").lower()
        if status == "done":
            done += 1
        if status == "blocked":
            blocked += 1
    if total == 0:
        return None
    quality = (done / total) - (blocked / total) * 0.5
    return max(0.0, min(1.0, quality))


def _calculate_resource_utilization(
    resources: list[dict[str, Any]], work_items: list[dict[str, Any]]
) -> float | None:
    if not resources:
        return None
    utilization_values: list[float] = []
    for resource in resources:
        metadata = resource.get("data", {}).get("metadata") or {}
        utilization = _coerce_float(metadata.get("utilization"))
        if utilization is None:
            utilization_pct = _coerce_float(metadata.get("utilization_pct"))
            if utilization_pct is not None:
                utilization = utilization_pct / 100.0
        if utilization is not None:
            utilization_values.append(utilization)

    if utilization_values:
        return sum(utilization_values) / len(utilization_values)

    active_items = [
        item
        for item in work_items
        if (item.get("data", {}).get("status") or "").lower() in {"todo", "in_progress"}
    ]
    if not active_items:
        return 0.0
    estimated = len(active_items) / (len(resources) * 3)
    return min(1.5, estimated)


def _matches_project(data: dict[str, Any] | None, project_id: str) -> bool:
    if not data:
        return False
    if data.get("project_id") == project_id:
        return True
    metadata = data.get("metadata") or {}
    if metadata.get("project_id") == project_id:
        return True
    if metadata.get("project") == project_id:
        return True
    if data.get("portfolio_id") == project_id:
        return True
    return False


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        return date.fromisoformat(value)
    except ValueError:
        return None


def _coerce_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_actual_cost(data: dict[str, Any]) -> float | None:
    metadata = data.get("metadata") or {}
    for key in ("actual_cost", "actual", "spent", "actual_spend", "cost_actual"):
        value = _coerce_float(metadata.get(key))
        if value is not None:
            return value
    return None


def _forecast_metric(values: list[float]) -> tuple[float | None, float | None, str | None]:
    if not values:
        return None, None, None
    if len(values) < 2:
        return 0.0, values[-1], "moving_average"
    slope, intercept = _linear_regression(values)
    if slope is None or intercept is None:
        return None, None, None
    forecast = slope * len(values) + intercept
    return slope, forecast, "linear_regression"


def _linear_regression(values: list[float]) -> tuple[float | None, float | None]:
    n = len(values)
    if n < 2:
        return None, None
    x_values = list(range(n))
    sum_x = sum(x_values)
    sum_y = sum(values)
    sum_xx = sum(x * x for x in x_values)
    sum_xy = sum(x * y for x, y in zip(x_values, values))
    denominator = n * sum_xx - sum_x * sum_x
    if denominator == 0:
        return None, None
    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n
    return slope, intercept


def _compute_recent_change(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    return values[-1] - values[0]


def _build_summary(snapshot: KpiSnapshot) -> str:
    normalized_values = list(snapshot.normalized.values())
    if not normalized_values:
        return "No KPI data available to summarize."
    average = sum(normalized_values) / len(normalized_values)
    if average >= 0.85:
        status = "healthy"
    elif average >= 0.7:
        status = "stable"
    else:
        status = "at risk"
    return f"Overall project health is {status} with an average KPI score of {average:.2f}."
