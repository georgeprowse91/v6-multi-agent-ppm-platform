from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for root in (SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from conflict_store import get_conflict_store  # noqa: E402
from data_sync_queue import enqueue_sync_job, get_queue_client  # noqa: E402
from data_sync_status import get_status_store  # noqa: E402
from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from security.auth import AuthTenantMiddleware  # noqa: E402
from security.lineage import mask_lineage_payload  # noqa: E402
from sync_log_store import get_sync_log_store  # noqa: E402
from sync_registry import (  # noqa: E402
    build_default_registry,
    get_registry,
    get_scheduler,
)

logger = logging.getLogger("data-sync-service")
logging.basicConfig(level=logging.INFO)

DEFAULT_RULES_DIR = REPO_ROOT / "services" / "data-sync-service" / "rules"


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "data-sync-service"


class SyncRunRequest(BaseModel):
    connector: str | None = None
    dry_run: bool = True


class SyncRule(BaseModel):
    id: str
    description: str | None = None
    source: str
    target: str
    mode: str = "merge"
    filters: dict[str, Any] | None = None


class SyncRunResponse(BaseModel):
    job_id: str
    status: str
    started_at: datetime
    planned_rules: list[str]


class SyncStatusResponse(BaseModel):
    job_id: str
    status: str
    created_at: str
    updated_at: str
    connector: str | None
    details: dict[str, Any]


class SyncJobSummary(BaseModel):
    connector: str
    entity: str
    interval_seconds: int
    strategy: str
    description: str
    last_run_at: str | None
    next_run_at: str | None
    last_status: str | None
    last_latency_ms: int | None
    last_error: str | None


class SyncLogResponse(BaseModel):
    log_id: str
    connector: str
    entity: str
    status: str
    latency_ms: int
    errors: list[str]
    last_sync_at: str
    created_at: str
    details: dict[str, Any]


class SyncSummaryResponse(BaseModel):
    connector: str
    entity: str
    total_runs: int
    success_runs: int
    error_runs: int
    success_rate: float
    last_sync_at: str | None
    last_status: str | None


class ConflictResponse(BaseModel):
    conflict_id: str
    connector: str
    entity: str
    task_id: str | None
    external_id: str | None
    strategy: str
    reason: str
    internal_updated_at: str | None
    external_updated_at: str | None
    created_at: str
    details: dict[str, Any]


app = FastAPI(title="Data Sync Service", version="0.1.0")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz"})
configure_tracing("data-sync-service")
configure_metrics("data-sync-service")
app.add_middleware(TraceMiddleware, service_name="data-sync-service")
app.add_middleware(RequestMetricsMiddleware, service_name="data-sync-service")

build_default_registry()
scheduler = get_scheduler()

data_sync_jobs_total = configure_metrics("data-sync-service").create_counter(
    name="data_sync_jobs_total",
    description="Data sync jobs processed",
    unit="1",
)


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()


@app.on_event("startup")
async def _start_scheduler() -> None:
    scheduler.start()


@app.on_event("shutdown")
async def _stop_scheduler() -> None:
    scheduler.stop()


def _load_rules() -> list[SyncRule]:
    rules_dir = Path(os.getenv("DATA_SYNC_RULES_DIR", str(DEFAULT_RULES_DIR)))
    rules: list[SyncRule] = []
    for path in sorted(rules_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        if not data:
            continue
        rule = SyncRule(**data)
        rules.append(rule)
    return rules


def _mask_lineage(details: dict[str, Any]) -> dict[str, Any]:
    if "lineage" not in details:
        return details
    masked = dict(details)
    masked["lineage"] = mask_lineage_payload(details["lineage"])
    return masked


@app.post("/sync/run", response_model=SyncRunResponse)
async def run_sync(request: SyncRunRequest) -> SyncRunResponse:
    rules = _load_rules()
    planned = [rule.id for rule in rules]
    job_id = str(uuid4())
    status_store = get_status_store()
    status_store.create(job_id, request.connector, "planned")

    queue_client = get_queue_client()
    enqueue_sync_job(
        queue_client,
        job_id=job_id,
        connector=request.connector,
        dry_run=request.dry_run,
        rules=planned,
    )
    status_store.update(job_id, "queued")
    data_sync_jobs_total.add(1, {"status": "queued"})

    logger.info(
        "sync_run_triggered",
        extra={
            "job_id": job_id,
            "connector": request.connector,
            "dry_run": request.dry_run,
            "rules": planned,
        },
    )

    return SyncRunResponse(
        job_id=job_id,
        status="queued",
        started_at=datetime.now(timezone.utc),
        planned_rules=planned,
    )


@app.get("/sync/status/{job_id}", response_model=SyncStatusResponse)
async def get_sync_status(job_id: str) -> SyncStatusResponse:
    status_store = get_status_store()
    job = status_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    payload = job.__dict__.copy()
    payload["details"] = _mask_lineage(payload.get("details", {}))
    return SyncStatusResponse(**payload)


@app.get("/sync/jobs", response_model=list[SyncJobSummary])
async def list_sync_jobs() -> list[SyncJobSummary]:
    registry = get_registry()
    jobs: list[SyncJobSummary] = []
    for job in registry.list_jobs():
        state = scheduler.get_state(job.connector, job.entity)
        jobs.append(
            SyncJobSummary(
                connector=job.connector,
                entity=job.entity,
                interval_seconds=job.interval_seconds,
                strategy=job.strategy,
                description=job.description,
                last_run_at=state.last_run_at,
                next_run_at=state.next_run_at,
                last_status=state.last_status,
                last_latency_ms=state.last_latency_ms,
                last_error=state.last_error,
            )
        )
    return jobs


@app.post("/sync/jobs/{connector}/{entity}/run", response_model=SyncLogResponse)
async def run_sync_job(connector: str, entity: str, dry_run: bool = False) -> SyncLogResponse:
    try:
        result = scheduler.run_job(connector, entity, dry_run=dry_run)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    log_store = get_sync_log_store()
    summary = log_store.list_recent(limit=1)
    if summary:
        return SyncLogResponse(**summary[0].__dict__)
    return SyncLogResponse(
        log_id="n/a",
        connector=connector,
        entity=entity,
        status=result.status,
        latency_ms=result.latency_ms,
        errors=result.errors,
        last_sync_at=result.last_sync_at,
        created_at=result.last_sync_at,
        details=result.details,
    )


@app.get("/sync/logs", response_model=list[SyncLogResponse])
async def list_sync_logs(limit: int = 50) -> list[SyncLogResponse]:
    log_store = get_sync_log_store()
    return [SyncLogResponse(**log.__dict__) for log in log_store.list_recent(limit=limit)]


@app.get("/sync/summary", response_model=list[SyncSummaryResponse])
async def get_sync_summary() -> list[SyncSummaryResponse]:
    log_store = get_sync_log_store()
    registry = get_registry()
    summaries: list[SyncSummaryResponse] = []
    for job in registry.list_jobs():
        stats = log_store.summary(connector=job.connector)
        state = scheduler.get_state(job.connector, job.entity)
        summaries.append(
            SyncSummaryResponse(
                connector=job.connector,
                entity=job.entity,
                total_runs=stats["total_runs"],
                success_runs=stats["success_runs"],
                error_runs=stats["error_runs"],
                success_rate=stats["success_rate"],
                last_sync_at=stats["last_sync_at"],
                last_status=state.last_status,
            )
        )
    return summaries


@app.get("/sync/conflicts", response_model=list[ConflictResponse])
async def list_conflicts(limit: int = 50) -> list[ConflictResponse]:
    conflict_store = get_conflict_store()
    return [
        ConflictResponse(**record.__dict__) for record in conflict_store.list_recent(limit=limit)
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
