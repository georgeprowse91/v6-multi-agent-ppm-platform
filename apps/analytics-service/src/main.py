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
for root in (SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from observability.metrics import (  # noqa: E402
    RequestMetricsMiddleware,
    build_kpi_handles,
    configure_metrics,
)
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
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
    global scheduler, run_loop_task
    db_path = Path(
        os.getenv("ANALYTICS_SCHEDULER_DB", "apps/analytics-service/storage/scheduler.db")
    )
    scheduler = AnalyticsScheduler(db_path)
    run_loop_task = asyncio.create_task(_run_scheduler_loop())
    logger.info("analytics_scheduler_started", extra={"db_path": str(db_path)})


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
