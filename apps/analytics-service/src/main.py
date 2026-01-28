from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from opentelemetry.metrics import Observation
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for root in (REPO_ROOT, SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from agents.common.health_recommendations import (  # noqa: E402
    generate_recommendations,
    identify_health_concerns,
)
from agents.common.metrics_catalog import normalize_metric_value  # noqa: E402
from agents.runtime.src.state_store import TenantStateStore  # noqa: E402
from observability.metrics import (  # noqa: E402
    RequestMetricsMiddleware,
    build_kpi_handles,
    configure_metrics,
)
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from health import HealthSnapshotStore  # noqa: E402
from scheduler import AnalyticsScheduler  # noqa: E402
from security.auth import AuthTenantMiddleware  # noqa: E402

logger = logging.getLogger("analytics-service")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Analytics Service", version="0.1.0")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/health", "/healthz"})
configure_tracing("analytics-service")
configure_metrics("analytics-service")
app.add_middleware(TraceMiddleware, service_name="analytics-service")
app.add_middleware(RequestMetricsMiddleware, service_name="analytics-service")

scheduler: AnalyticsScheduler | None = None
run_loop_task: asyncio.Task | None = None
kpi_handles = build_kpi_handles("analytics-service")
_last_scheduler_run_ts: float | None = None
health_snapshot_store: HealthSnapshotStore | None = None

DEFAULT_HEALTH_HISTORY_LIMIT = int(os.getenv("ANALYTICS_HEALTH_HISTORY_LIMIT", "20"))
DEFAULT_HEALTH_SNAPSHOT_DB = os.getenv(
    "ANALYTICS_HEALTH_SNAPSHOT_DB",
    "apps/analytics-service/storage/health_snapshots.json",
)
DEFAULT_LIFECYCLE_HEALTH_STORE = os.getenv(
    "PROJECT_HEALTH_HISTORY_PATH",
    "data/project_health_history.json",
)

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


class WhatIfRequest(BaseModel):
    scenario: str
    adjustments: dict[str, Any] = Field(default_factory=dict)


class WhatIfResponse(BaseModel):
    project_id: str
    scenario_id: str
    status: str
    message: str


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


def _build_synthetic_health(project_id: str) -> dict[str, Any]:
    seed = sum(ord(char) for char in project_id)
    schedule_variance = ((seed % 25) - 12) / 100
    cost_variance = ((seed // 3 % 20) - 7) / 100
    risk_score = (seed % 30) / 100
    quality_score = 0.75 + (seed % 15) / 100
    resource_utilization = 0.7 + (seed % 25) / 100

    raw_metrics = {
        "schedule_variance": schedule_variance,
        "cost_variance": cost_variance,
        "risk_score": risk_score,
        "quality_score": quality_score,
        "resource_utilization": resource_utilization,
    }

    schedule_health = normalize_metric_value("schedule_variance", schedule_variance)
    cost_health = normalize_metric_value("cost_variance", cost_variance)
    risk_health = normalize_metric_value("risk_score", risk_score)
    quality_health = normalize_metric_value("quality_score", quality_score)
    resource_health = normalize_metric_value("resource_utilization", resource_utilization)

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
        "project_id": project_id,
        "composite_score": composite_score,
        "health_status": _determine_health_status(composite_score),
        "metrics": {
            "schedule": {
                "score": schedule_health,
                "status": _metric_status(schedule_health),
                "raw": schedule_variance,
            },
            "cost": {
                "score": cost_health,
                "status": _metric_status(cost_health),
                "raw": cost_variance,
            },
            "risk": {
                "score": risk_health,
                "status": _metric_status(risk_health),
                "raw": risk_score,
            },
            "quality": {
                "score": quality_health,
                "status": _metric_status(quality_health),
                "raw": quality_score,
            },
            "resource": {
                "score": resource_health,
                "status": _metric_status(resource_health),
                "raw": resource_utilization,
            },
        },
        "raw_metrics": raw_metrics,
        "concerns": concerns,
        "warnings": warnings,
        "recommendations": generate_recommendations(concerns),
        "monitored_at": datetime.now(timezone.utc).isoformat(),
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
    global scheduler, run_loop_task, health_snapshot_store
    db_path = Path(
        os.getenv("ANALYTICS_SCHEDULER_DB", "apps/analytics-service/storage/scheduler.db")
    )
    scheduler = AnalyticsScheduler(db_path)
    run_loop_task = asyncio.create_task(_run_scheduler_loop())
    logger.info("analytics_scheduler_started", extra={"db_path": str(db_path)})
    health_snapshot_store = HealthSnapshotStore(
        Path(DEFAULT_HEALTH_SNAPSHOT_DB), history_limit=DEFAULT_HEALTH_HISTORY_LIMIT
    )


@app.on_event("shutdown")
async def shutdown() -> None:
    if run_loop_task:
        run_loop_task.cancel()


@app.get("/health", response_model=HealthResponse)
@app.get("/healthz", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@app.get("/jobs", response_model=list[JobResponse])
async def list_jobs(request: Request) -> list[JobResponse]:
    assert scheduler is not None
    tenant_id = request.state.auth.tenant_id
    return [_job_to_response(job) for job in scheduler.list_jobs(tenant_id)]


@app.post("/jobs", response_model=JobResponse)
async def create_job(request: Request, payload: JobRequest) -> JobResponse:
    assert scheduler is not None
    tenant_id = request.state.auth.tenant_id
    job = scheduler.schedule_job(payload.name, payload.interval_minutes, tenant_id, payload.payload)
    jobs_scheduled.add(1, {"job_name": job.name, "tenant_id": tenant_id})
    kpi_handles.requests.add(1, {"operation": "schedule_job", "tenant_id": tenant_id})
    return _job_to_response(job)


@app.patch("/jobs/{job_id}", response_model=JobResponse)
async def update_job(job_id: str, request: Request, payload: JobUpdateRequest) -> JobResponse:
    assert scheduler is not None
    tenant_id = request.state.auth.tenant_id
    job = scheduler.update_job(job_id, tenant_id, payload.interval_minutes, payload.enabled)
    if not job:
        kpi_handles.errors.add(1, {"operation": "update_job", "tenant_id": tenant_id})
        raise HTTPException(status_code=404, detail="Job not found")
    kpi_handles.requests.add(1, {"operation": "update_job", "tenant_id": tenant_id})
    return _job_to_response(job)


@app.post("/jobs/{job_id}/run", response_model=JobResponse)
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


@app.get("/api/projects/{project_id}/health", response_model=ProjectHealthResponse)
async def get_project_health(project_id: str, request: Request) -> ProjectHealthResponse:
    assert health_snapshot_store is not None
    tenant_id = request.state.auth.tenant_id
    lifecycle_data = _load_lifecycle_health(tenant_id, project_id)
    if lifecycle_data is None:
        lifecycle_data = _build_synthetic_health(project_id)
    if lifecycle_data.get("project_id") is None:
        lifecycle_data["project_id"] = project_id
    health_snapshot_store.add_snapshot(tenant_id, project_id, lifecycle_data)
    kpi_handles.requests.add(1, {"operation": "get_project_health", "tenant_id": tenant_id})
    return _coerce_health_response(lifecycle_data)


@app.get("/api/projects/{project_id}/health/trends", response_model=HealthTrendResponse)
async def get_project_health_trends(
    project_id: str, request: Request
) -> HealthTrendResponse:
    assert health_snapshot_store is not None
    tenant_id = request.state.auth.tenant_id
    snapshots = health_snapshot_store.list_snapshots(tenant_id, project_id)
    if not snapshots:
        snapshot = _build_synthetic_health(project_id)
        snapshots = health_snapshot_store.add_snapshot(tenant_id, project_id, snapshot)
    points: list[HealthTrendPoint] = []
    for snapshot in snapshots:
        metrics = snapshot.get("metrics", {})
        points.append(
            HealthTrendPoint(
                timestamp=str(snapshot.get("monitored_at", "")),
                composite_score=float(snapshot.get("composite_score", 0.0)),
                metrics={
                    "schedule": float(metrics.get("schedule", {}).get("score", 0.0)),
                    "cost": float(metrics.get("cost", {}).get("score", 0.0)),
                    "risk": float(metrics.get("risk", {}).get("score", 0.0)),
                    "resource": float(metrics.get("resource", {}).get("score", 0.0)),
                    "quality": float(metrics.get("quality", {}).get("score", 0.0)),
                },
            )
        )
    kpi_handles.requests.add(1, {"operation": "get_project_health_trends", "tenant_id": tenant_id})
    return HealthTrendResponse(
        project_id=project_id,
        points=points,
        history_limit=health_snapshot_store.history_limit,
    )


@app.post("/api/projects/{project_id}/health/what-if", response_model=WhatIfResponse)
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
