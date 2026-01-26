from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from fastapi import FastAPI
from pydantic import BaseModel, Field

logger = logging.getLogger("data-sync-service")
logging.basicConfig(level=logging.INFO)

REPO_ROOT = Path(__file__).resolve().parents[3]
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


app = FastAPI(title="Data Sync Service", version="0.1.0")


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


@app.post("/sync/run", response_model=SyncRunResponse)
async def run_sync(request: SyncRunRequest) -> SyncRunResponse:
    rules = _load_rules()
    planned = [rule.id for rule in rules]
    job_id = str(uuid4())

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
        status="planned",
        started_at=datetime.now(timezone.utc),
        planned_rules=planned,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
