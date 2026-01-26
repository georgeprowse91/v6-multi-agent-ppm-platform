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
if str(SECURITY_ROOT) not in sys.path:
    sys.path.insert(0, str(SECURITY_ROOT))

from data_sync_queue import get_queue_client  # noqa: E402
from data_sync_status import get_status_store  # noqa: E402
from security.auth import AuthTenantMiddleware  # noqa: E402
from security.lineage import mask_lineage_payload  # noqa: E402

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


app = FastAPI(title="Data Sync Service", version="0.1.0")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz"})


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()


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
    queue_client.send(
        {
            "job_id": job_id,
            "connector": request.connector,
            "dry_run": request.dry_run,
            "rules": planned,
        }
    )
    status_store.update(job_id, "queued")

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
