from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Request
from opentelemetry.metrics import Observation
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for root in (REPO_ROOT, SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from health import HealthSnapshotStore  # noqa: E402
from kpi_engine import (  # noqa: E402
    AnalyticsDataClient,
    AnalyticsKpiEngine,
    KpiSnapshot,
    apply_what_if_adjustments,
    compute_kpi_trends,
    generate_narrative,
)
from metrics_store import MetricsStore  # noqa: E402
from observability.metrics import (  # noqa: E402
    RequestMetricsMiddleware,
    build_kpi_handles,
    configure_metrics,
)
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from scheduler import AnalyticsScheduler  # noqa: E402
from security.auth import AuthTenantMiddleware  # noqa: E402
from packages.version import API_VERSION

from agents.common.health_recommendations import (  # noqa: E402
    generate_recommendations,
    identify_health_concerns,
)
from agents.common.metrics_catalog import normalize_metric_value  # noqa: E402
from agents.runtime.src.state_store import TenantStateStore  # noqa: E402

logger = logging.getLogger("analytics-service")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Analytics Service", version=API_VERSION, openapi_prefix="/v1")
api_router = APIRouter(prefix="/v1")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/health", "/healthz", "/version"})
configure_tracing("analytics-service")
configure_metrics("analytics-service")
app.add_middleware(TraceMiddleware, service_name="analytics-service")
app.add_middleware(RequestMetricsMiddleware, service_name="analytics-service")

scheduler: AnalyticsScheduler | None = None
run_loop_task: asyncio.Task | None = None
kpi_handles = build_kpi_handles("analytics-service")
_last_scheduler_run_ts: float | None = None
health_snapshot_store: HealthSnapshotStore | None = None
metrics_store: MetricsStore | None = None
kpi_engine: AnalyticsKpiEngine | None = None
data_client: AnalyticsDataClient | None = None

DEFAULT_HEALTH_HISTORY_LIMIT = int(os.getenv("ANALYTICS_HEALTH_HISTORY_LIMIT", "20"))
DEFAULT_HEALTH_SNAPSHOT_DB = os.getenv(
    "ANALYTICS_HEALTH_SNAPSHOT_DB",
    "apps/analytics-service/storage/health_snapshots.json",
)
DEFAULT_LIFECYCLE_HEALTH_STORE = os.getenv(
    "PROJECT_HEALTH_HISTORY_PATH",
    "data/project_health_history.json",
)
DEFAULT_METRICS_DB = os.getenv(
    "ANALYTICS_METRICS_DB",
    "apps/analytics-service/storage/metrics.db",
)
DEFAULT_DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://localhost:8081")

jobs_scheduled = configure_metrics("analytics-service").create_counter(
    name="analytics_jobs_scheduled_total",
    description="Number of analytics jobs scheduled",
    unit="1",
)
jobs_completed = configure_metrics("analytics-service").create_counter(
    name="analytics_jobs_completed_total",
    description="Number of analytics jobs completed",
    unit="1",
)
jobs_failed = configure_metrics("analytics-service").create_counter(
    name="analytics_jobs_failed_total",
    description="Number of analytics jobs failed",
    unit="1",
)


def _scheduler_last_run_callback(options):  # pragma: no cover - OTel callback signature
    if _last_scheduler_run_ts is None:
        return []
    return [Observation(_last_scheduler_run_ts, {})]


configure_metrics("analytics-service").create_observable_gauge(
    name="analytics_scheduler_last_run_timestamp",
    callbacks=[_scheduler_last_run_callback],
    description="Last scheduler run epoch timestamp",
    unit="s",
)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "analytics-service"


class JobRequest(BaseModel):
    name: str
    interval_minutes: int = Field(..., ge=1, le=1440)
    payload: dict[str, Any] = Field(default_factory=dict)


class JobUpdateRequest(BaseModel):
    interval_minutes: int | None = Field(default=None, ge=1, le=1440)
    enabled: bool | None = None


class JobResponse(BaseModel):
    job_id: str
    name: str
    interval_minutes: int
    payload: dict[str, Any]
    enabled: bool
    next_run: datetime
    last_run: datetime | None
    status: str


class HealthMetric(BaseModel):
    score: float
    status: str
    raw: float | None = None


class ProjectHealthResponse(BaseModel):
    project_id: str
    composite_score: float
    health_status: str
    metrics: dict[str, HealthMetric]
    concerns: list[str]
    warnings: list[dict[str, Any]]
    recommendations: list[str]
    monitored_at: str


class HealthTrendPoint(BaseModel):
    timestamp: str
    composite_score: float
    metrics: dict[str, float]


class HealthTrendResponse(BaseModel):
    project_id: str
    points: list[HealthTrendPoint]
    history_limit: int


class KpiTrendPointResponse(BaseModel):
    timestamp: str
    value: float | None


class KpiTrendSeriesResponse(BaseModel):
    metric: str
    points: list[KpiTrendPointResponse]
    slope: float | None
    forecast: float | None
    forecast_method: str | None
    recent_change: float | None


class KpiTrendResponse(BaseModel):
    project_id: str
    computed_at: str
    period_count: int
    series: list[KpiTrendSeriesResponse]
    warnings: list[dict[str, Any]]


class WhatIfRequest(BaseModel):
    scenario: str
    adjustments: dict[str, Any] = Field(default_factory=dict)


class WhatIfResponse(BaseModel):
    project_id: str
    scenario_id: str
    status: str
    message: str


class KpiMetricResponse(BaseModel):
    name: str
    value: float | None
    normalized: float


class ProjectKpiResponse(BaseModel):
    project_id: str
    metrics: list[KpiMetricResponse]
    computed_at: str


class NarrativeResponse(BaseModel):
    project_id: str
    summary: str
    highlights: list[str]
    risks: list[str]
    opportunities: list[str]
    data_quality_notes: list[str]
    computed_at: str


class WhatIfDetailResponse(BaseModel):
    project_id: str
    scenario_id: str
    status: str
    baseline: ProjectKpiResponse
    adjusted: ProjectKpiResponse
    narrative: NarrativeResponse


def _job_to_response(job) -> JobResponse:
    return JobResponse(
        job_id=job.job_id,
        name=job.name,
        interval_minutes=job.interval_minutes,
        payload=job.payload,
        enabled=job.enabled,
        next_run=job.next_run,
        last_run=job.last_run,
        status=job.status,
    )


def _parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def _determine_health_status(composite_score: float) -> str:
    if composite_score >= 0.85:
        return "Healthy"
    if composite_score >= 0.70:
        return "At Risk"
    return "Critical"


def _metric_status(score: float) -> str:
    if score >= 0.85:
        return "green"
    if score >= 0.70:
        return "yellow"
    return "red"


def _detect_warnings(raw_metrics: dict[str, float | None]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    schedule_variance = raw_metrics.get("schedule_variance")
    if schedule_variance is not None and schedule_variance < -0.1:
        warnings.append(
            {"type": "schedule_slip", "message": "Schedule slipping beyond 10% threshold"}
        )
    cost_variance = raw_metrics.get("cost_variance")
    if cost_variance is not None and cost_variance > 0.1:
        warnings.append({"type": "cost_overrun", "message": "Cost variance exceeds 10%"})
    risk_score = raw_metrics.get("risk_score")
    if risk_score is not None and risk_score > 0.35:
        warnings.append({"type": "risk_spike", "message": "Risk exposure trending high"})
    resource_utilization = raw_metrics.get("resource_utilization")
    if resource_utilization is not None and resource_utilization > 0.95:
        warnings.append({"type": "resource_strain", "message": "Resource load above 95%"})
    return warnings


def _detect_trend_warnings(series_list: list[KpiTrendSeriesResponse]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    forecast_lookup = {series.metric: series.forecast for series in series_list}
    schedule_forecast = forecast_lookup.get("schedule_variance")
    if schedule_forecast is not None and schedule_forecast < -0.1:
        warnings.append(
            {
                "type": "schedule_forecast_slip",
                "message": "Forecast shows schedule variance slipping beyond 10%.",
                "forecast": schedule_forecast,
            }
        )
    cost_forecast = forecast_lookup.get("cost_variance")
    if cost_forecast is not None and cost_forecast > 0.1:
        warnings.append(
            {
                "type": "cost_forecast_overrun",
                "message": "Forecast suggests cost variance above 10%.",
                "forecast": cost_forecast,
            }
        )
    risk_forecast = forecast_lookup.get("risk_score")
    if risk_forecast is not None and risk_forecast > 0.35:
        warnings.append(
            {
                "type": "risk_forecast_spike",
                "message": "Risk exposure forecast trending high.",
                "forecast": risk_forecast,
            }
        )
    resource_forecast = forecast_lookup.get("resource_utilization")
    if resource_forecast is not None and resource_forecast > 0.95:
        warnings.append(
            {
                "type": "resource_forecast_strain",
                "message": "Resource utilization forecast exceeds 95%.",
                "forecast": resource_forecast,
            }
        )
    return warnings


def _load_lifecycle_health(tenant_id: str, project_id: str) -> dict[str, Any] | None:
    path = Path(DEFAULT_LIFECYCLE_HEALTH_STORE)
    if not path.exists():
        return None
    store = TenantStateStore(path)
    records = [record for record in store.list(tenant_id) if record.get("project_id") == project_id]
    if not records:
        return None
    records = sorted(records, key=lambda item: _parse_timestamp(item.get("monitored_at")))
    return records[-1]


def _build_health_from_kpis(snapshot: KpiSnapshot) -> dict[str, Any]:
    raw_metrics = snapshot.metrics
    schedule_health = snapshot.normalized.get("schedule_variance", 0.0)
    cost_health = snapshot.normalized.get("cost_variance", 0.0)
    risk_health = snapshot.normalized.get("risk_score", 0.0)
    quality_health = snapshot.normalized.get("quality_score", 0.0)
    resource_health = snapshot.normalized.get("resource_utilization", 0.0)

    weights = {"schedule": 0.25, "cost": 0.25, "risk": 0.2, "quality": 0.15, "resource": 0.15}
    composite_score = (
        schedule_health * weights["schedule"]
        + cost_health * weights["cost"]
        + risk_health * weights["risk"]
        + quality_health * weights["quality"]
        + resource_health * weights["resource"]
    )

    concerns = identify_health_concerns(
        {
            "schedule": schedule_health,
            "cost": cost_health,
            "risk": risk_health,
            "quality": quality_health,
            "resource": resource_health,
        }
    )
    warnings = _detect_warnings(raw_metrics)

    return {
        "project_id": snapshot.project_id,
        "composite_score": composite_score,
        "health_status": _determine_health_status(composite_score),
        "metrics": {
            "schedule": {
                "score": schedule_health,
                "status": _metric_status(schedule_health),
                "raw": raw_metrics.get("schedule_variance"),
            },
            "cost": {
                "score": cost_health,
                "status": _metric_status(cost_health),
                "raw": raw_metrics.get("cost_variance"),
            },
            "risk": {
                "score": risk_health,
                "status": _metric_status(risk_health),
                "raw": raw_metrics.get("risk_score"),
            },
            "quality": {
                "score": quality_health,
                "status": _metric_status(quality_health),
                "raw": raw_metrics.get("quality_score"),
            },
            "resource": {
                "score": resource_health,
                "status": _metric_status(resource_health),
                "raw": raw_metrics.get("resource_utilization"),
            },
        },
        "raw_metrics": raw_metrics,
        "concerns": concerns,
        "warnings": warnings,
        "recommendations": generate_recommendations(concerns),
        "monitored_at": snapshot.computed_at.isoformat(),
    }


def _coerce_health_response(data: dict[str, Any]) -> ProjectHealthResponse:
    metrics = {
        key: HealthMetric(
            score=float(value.get("score", 0.0)),
            status=str(value.get("status", "red")),
            raw=value.get("raw"),
        )
        for key, value in data.get("metrics", {}).items()
        if isinstance(value, dict)
    }
    return ProjectHealthResponse(
        project_id=str(data.get("project_id", "")),
        composite_score=float(data.get("composite_score", 0.0)),
        health_status=str(data.get("health_status", "Unknown")),
        metrics=metrics,
        concerns=list(data.get("concerns") or []),
        warnings=list(data.get("warnings") or []),
        recommendations=list(data.get("recommendations") or []),
        monitored_at=str(data.get("monitored_at", "")),
    )


async def _run_scheduler_loop() -> None:
    assert scheduler is not None
    while True:
        now = datetime.now(timezone.utc)
        global _last_scheduler_run_ts
        _last_scheduler_run_ts = now.timestamp()
        due_jobs = scheduler.due_jobs(now)
        for job in due_jobs:
            try:
                scheduler.record_run(job, "running")
                await asyncio.sleep(0)
                scheduler.record_run(job, "completed")
                jobs_completed.add(1, {"job_name": job.name, "tenant_id": job.tenant_id})
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception(
                    "analytics_job_failed", extra={"job_id": job.job_id, "error": str(exc)}
                )
                scheduler.record_run(job, "failed")
                jobs_failed.add(1, {"job_name": job.name, "tenant_id": job.tenant_id})
        await asyncio.sleep(5)


@app.on_event("startup")
async def startup() -> None:
    global scheduler, run_loop_task, health_snapshot_store, metrics_store, kpi_engine, data_client
    db_path = Path(
        os.getenv("ANALYTICS_SCHEDULER_DB", "apps/analytics-service/storage/scheduler.db")
    )
    scheduler = AnalyticsScheduler(db_path)
    run_loop_task = asyncio.create_task(_run_scheduler_loop())
    logger.info("analytics_scheduler_started", extra={"db_path": str(db_path)})
    health_snapshot_store = HealthSnapshotStore(
        Path(DEFAULT_HEALTH_SNAPSHOT_DB), history_limit=DEFAULT_HEALTH_HISTORY_LIMIT
    )
    metrics_store = MetricsStore(Path(DEFAULT_METRICS_DB))
    data_client = AnalyticsDataClient(DEFAULT_DATA_SERVICE_URL)
    kpi_engine = AnalyticsKpiEngine(data_client, metrics_store)


@app.on_event("shutdown")
async def shutdown() -> None:
    if run_loop_task:
        run_loop_task.cancel()
    if data_client:
        await data_client.close()


@app.get("/health", response_model=HealthResponse)
@app.get("/healthz", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@app.get("/version")
async def version() -> dict[str, str]:
    return {
        "service": "analytics-service",
        "api_version": API_VERSION,
        "build_sha": os.getenv("BUILD_SHA", "unknown"),
    }


@api_router.get("/jobs", response_model=list[JobResponse])
async def list_jobs(request: Request) -> list[JobResponse]:
    assert scheduler is not None
    tenant_id = request.state.auth.tenant_id
    return [_job_to_response(job) for job in scheduler.list_jobs(tenant_id)]


@api_router.post("/jobs", response_model=JobResponse)
async def create_job(request: Request, payload: JobRequest) -> JobResponse:
    assert scheduler is not None
    tenant_id = request.state.auth.tenant_id
    job = scheduler.schedule_job(payload.name, payload.interval_minutes, tenant_id, payload.payload)
    jobs_scheduled.add(1, {"job_name": job.name, "tenant_id": tenant_id})
    kpi_handles.requests.add(1, {"operation": "schedule_job", "tenant_id": tenant_id})
    return _job_to_response(job)


@api_router.patch("/jobs/{job_id}", response_model=JobResponse)
async def update_job(job_id: str, request: Request, payload: JobUpdateRequest) -> JobResponse:
    assert scheduler is not None
    tenant_id = request.state.auth.tenant_id
    job = scheduler.update_job(job_id, tenant_id, payload.interval_minutes, payload.enabled)
    if not job:
        kpi_handles.errors.add(1, {"operation": "update_job", "tenant_id": tenant_id})
        raise HTTPException(status_code=404, detail="Job not found")
    kpi_handles.requests.add(1, {"operation": "update_job", "tenant_id": tenant_id})
    return _job_to_response(job)


@api_router.post("/jobs/{job_id}/run", response_model=JobResponse)
async def run_job(job_id: str, request: Request) -> JobResponse:
    assert scheduler is not None
    tenant_id = request.state.auth.tenant_id
    job = scheduler.get_job(job_id, tenant_id)
    if not job:
        kpi_handles.errors.add(1, {"operation": "run_job", "tenant_id": tenant_id})
        raise HTTPException(status_code=404, detail="Job not found")
    updated = scheduler.record_run(job, "completed")
    jobs_completed.add(1, {"job_name": updated.name, "tenant_id": tenant_id})
    kpi_handles.requests.add(1, {"operation": "run_job", "tenant_id": tenant_id})
    return _job_to_response(updated)


@api_router.get("/api/projects/{project_id}/health", response_model=ProjectHealthResponse)
async def get_project_health(project_id: str, request: Request) -> ProjectHealthResponse:
    assert health_snapshot_store is not None
    assert kpi_engine is not None
    tenant_id = request.state.auth.tenant_id
    lifecycle_data = _load_lifecycle_health(tenant_id, project_id)
    if lifecycle_data is None:
        try:
            snapshot = await kpi_engine.compute_kpis(project_id, tenant_id)
            lifecycle_data = _build_health_from_kpis(snapshot)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception(
                "kpi_computation_failed", extra={"project_id": project_id, "error": str(exc)}
            )
            lifecycle_data = _build_health_from_kpis(
                KpiSnapshot(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    computed_at=datetime.now(timezone.utc),
                    metrics={
                        "schedule_variance": None,
                        "cost_variance": None,
                        "risk_score": None,
                        "quality_score": None,
                        "resource_utilization": None,
                    },
                    normalized={
                        "schedule_variance": 0.0,
                        "cost_variance": 0.0,
                        "risk_score": 0.0,
                        "quality_score": 0.0,
                        "resource_utilization": 0.0,
                    },
                )
            )
    if lifecycle_data.get("project_id") is None:
        lifecycle_data["project_id"] = project_id
    health_snapshot_store.add_snapshot(tenant_id, project_id, lifecycle_data)
    kpi_handles.requests.add(1, {"operation": "get_project_health", "tenant_id": tenant_id})
    return _coerce_health_response(lifecycle_data)


@api_router.get("/api/projects/{project_id}/health/trends", response_model=HealthTrendResponse)
async def get_project_health_trends(project_id: str, request: Request) -> HealthTrendResponse:
    assert health_snapshot_store is not None
    assert metrics_store is not None
    assert kpi_engine is not None
    tenant_id = request.state.auth.tenant_id
    snapshots = metrics_store.list_snapshots(
        tenant_id, project_id, limit=DEFAULT_HEALTH_HISTORY_LIMIT
    )
    points: list[HealthTrendPoint] = []
    for snapshot in snapshots:
        points.append(
            HealthTrendPoint(
                timestamp=snapshot.captured_at.isoformat(),
                composite_score=float(
                    sum(
                        normalize_metric_value(name, value)
                        for name, value in snapshot.metrics.items()
                    )
                    / max(len(snapshot.metrics), 1)
                ),
                metrics={
                    "schedule": normalize_metric_value(
                        "schedule_variance", snapshot.metrics.get("schedule_variance")
                    ),
                    "cost": normalize_metric_value(
                        "cost_variance", snapshot.metrics.get("cost_variance")
                    ),
                    "risk": normalize_metric_value(
                        "risk_score", snapshot.metrics.get("risk_score")
                    ),
                    "resource": normalize_metric_value(
                        "resource_utilization", snapshot.metrics.get("resource_utilization")
                    ),
                    "quality": normalize_metric_value(
                        "quality_score", snapshot.metrics.get("quality_score")
                    ),
                },
            )
        )
    if not points:
        snapshot = await kpi_engine.compute_kpis(project_id, tenant_id)
        health_snapshot_store.add_snapshot(tenant_id, project_id, _build_health_from_kpis(snapshot))
        points.append(
            HealthTrendPoint(
                timestamp=snapshot.computed_at.isoformat(),
                composite_score=float(
                    sum(snapshot.normalized.values()) / max(len(snapshot.normalized), 1)
                ),
                metrics={
                    "schedule": snapshot.normalized.get("schedule_variance", 0.0),
                    "cost": snapshot.normalized.get("cost_variance", 0.0),
                    "risk": snapshot.normalized.get("risk_score", 0.0),
                    "resource": snapshot.normalized.get("resource_utilization", 0.0),
                    "quality": snapshot.normalized.get("quality_score", 0.0),
                },
            )
        )
    kpi_handles.requests.add(1, {"operation": "get_project_health_trends", "tenant_id": tenant_id})
    return HealthTrendResponse(
        project_id=project_id,
        points=points,
        history_limit=health_snapshot_store.history_limit,
    )


@api_router.get("/api/analytics/trends", response_model=KpiTrendResponse)
async def get_kpi_trends(project_id: str, request: Request) -> KpiTrendResponse:
    assert metrics_store is not None
    assert kpi_engine is not None
    tenant_id = request.state.auth.tenant_id
    snapshots = metrics_store.list_recent_snapshots(tenant_id, project_id, limit=6)
    if not snapshots:
        snapshot = await kpi_engine.compute_kpis(project_id, tenant_id)
        snapshots = metrics_store.list_recent_snapshots(tenant_id, project_id, limit=6)
        if not snapshots:
            snapshots = [
                metrics_store.add_snapshot(tenant_id, project_id, snapshot.metrics)
            ]
    trends = compute_kpi_trends(
        project_id=project_id,
        tenant_id=tenant_id,
        snapshots=snapshots,
        period_count=min(6, len(snapshots)),
    )
    series_response = [
        KpiTrendSeriesResponse(
            metric=series.metric,
            points=[
                KpiTrendPointResponse(
                    timestamp=point.timestamp.isoformat(),
                    value=point.value,
                )
                for point in series.points
            ],
            slope=series.slope,
            forecast=series.forecast,
            forecast_method=series.forecast_method,
            recent_change=series.recent_change,
        )
        for series in trends.series
    ]
    warnings = _detect_trend_warnings(series_response)
    kpi_handles.requests.add(1, {"operation": "get_kpi_trends", "tenant_id": tenant_id})
    return KpiTrendResponse(
        project_id=project_id,
        computed_at=trends.computed_at.isoformat(),
        period_count=trends.period_count,
        series=series_response,
        warnings=warnings,
    )


@api_router.post("/api/projects/{project_id}/health/what-if", response_model=WhatIfResponse)
async def request_health_what_if(
    project_id: str, request: Request, payload: WhatIfRequest
) -> WhatIfResponse:
    tenant_id = request.state.auth.tenant_id
    scenario_id = f"whatif-{project_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    logger.info(
        "health_what_if_requested",
        extra={
            "tenant_id": tenant_id,
            "project_id": project_id,
            "scenario": payload.scenario,
        },
    )
    kpi_handles.requests.add(1, {"operation": "health_what_if", "tenant_id": tenant_id})
    return WhatIfResponse(
        project_id=project_id,
        scenario_id=scenario_id,
        status="queued",
        message="What-if analysis queued. A detailed response will be available soon.",
    )


@api_router.get("/api/projects/{project_id}/kpis", response_model=ProjectKpiResponse)
async def get_project_kpis(project_id: str, request: Request) -> ProjectKpiResponse:
    assert kpi_engine is not None
    tenant_id = request.state.auth.tenant_id
    snapshot = await kpi_engine.compute_kpis(project_id, tenant_id)
    kpi_handles.requests.add(1, {"operation": "get_project_kpis", "tenant_id": tenant_id})
    return _snapshot_to_response(snapshot)


@api_router.get("/api/projects/{project_id}/kpis/narrative", response_model=NarrativeResponse)
async def get_project_kpi_narrative(project_id: str, request: Request) -> NarrativeResponse:
    assert kpi_engine is not None
    tenant_id = request.state.auth.tenant_id
    snapshot = await kpi_engine.compute_kpis(project_id, tenant_id)
    narrative = generate_narrative(snapshot)
    kpi_handles.requests.add(1, {"operation": "get_kpi_narrative", "tenant_id": tenant_id})
    return NarrativeResponse(
        project_id=project_id,
        summary=narrative.summary,
        highlights=narrative.highlights,
        risks=narrative.risks,
        opportunities=narrative.opportunities,
        data_quality_notes=narrative.data_quality_notes,
        computed_at=snapshot.computed_at.isoformat(),
    )


@api_router.post("/api/projects/{project_id}/kpis/what-if", response_model=WhatIfDetailResponse)
async def run_kpi_what_if(
    project_id: str, request: Request, payload: WhatIfRequest
) -> WhatIfDetailResponse:
    assert kpi_engine is not None
    tenant_id = request.state.auth.tenant_id
    baseline = await kpi_engine.compute_kpis(project_id, tenant_id)
    adjusted = apply_what_if_adjustments(baseline, payload.adjustments)
    narrative = generate_narrative(adjusted)
    scenario_id = f"whatif-{project_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    kpi_handles.requests.add(1, {"operation": "kpi_what_if", "tenant_id": tenant_id})
    return WhatIfDetailResponse(
        project_id=project_id,
        scenario_id=scenario_id,
        status="completed",
        baseline=_snapshot_to_response(baseline),
        adjusted=_snapshot_to_response(adjusted),
        narrative=NarrativeResponse(
            project_id=project_id,
            summary=narrative.summary,
            highlights=narrative.highlights,
            risks=narrative.risks,
            opportunities=narrative.opportunities,
            data_quality_notes=narrative.data_quality_notes,
            computed_at=adjusted.computed_at.isoformat(),
        ),
    )


def _snapshot_to_response(snapshot: KpiSnapshot) -> ProjectKpiResponse:
    metrics = [
        KpiMetricResponse(
            name=name,
            value=value,
            normalized=snapshot.normalized.get(name, 0.0),
        )
        for name, value in snapshot.metrics.items()
    ]
    return ProjectKpiResponse(
        project_id=snapshot.project_id,
        metrics=metrics,
        computed_at=snapshot.computed_at.isoformat(),
    )


app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
