from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from jsonschema import Draft202012Validator
from pydantic import BaseModel, Field

logger = logging.getLogger("audit-log")
logging.basicConfig(level=logging.INFO)

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "data" / "schemas" / "audit-event.schema.json"
DEFAULT_STORAGE_PATH = REPO_ROOT / "services" / "audit-log" / "storage" / "audit-events.jsonl"


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text())


def _validator() -> Draft202012Validator:
    return Draft202012Validator(_load_schema())


class AuditEventIn(BaseModel):
    id: str
    timestamp: datetime
    actor: dict[str, Any]
    action: str
    resource: dict[str, Any]
    outcome: str
    metadata: dict[str, Any] | None = None
    trace_id: str | None = None
    correlation_id: str | None = None


class AuditEventOut(BaseModel):
    id: str
    timestamp: datetime
    actor: dict[str, Any]
    action: str
    resource: dict[str, Any]
    outcome: str
    metadata: dict[str, Any] | None = None
    trace_id: str | None = None
    correlation_id: str | None = None


class AuditIngestResponse(BaseModel):
    status: str = "accepted"
    event: AuditEventOut


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "audit-log"


app = FastAPI(title="Audit Log Service", version="0.1.0")


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()


def _ensure_storage_path(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()


def _serialize_event(event: AuditEventOut) -> dict[str, Any]:
    payload = event.model_dump()
    payload["timestamp"] = event.timestamp.isoformat()
    return payload


@app.post("/audit/events", response_model=AuditIngestResponse)
async def ingest_event(payload: AuditEventIn) -> AuditIngestResponse:
    event_id = payload.id or str(uuid4())
    timestamp = payload.timestamp or datetime.now(timezone.utc)
    event = AuditEventOut(
        id=event_id,
        timestamp=timestamp,
        actor=payload.actor,
        action=payload.action,
        resource=payload.resource,
        outcome=payload.outcome,
        metadata=payload.metadata,
        trace_id=payload.trace_id,
        correlation_id=payload.correlation_id,
    )

    validator = _validator()
    errors = sorted(validator.iter_errors(_serialize_event(event)), key=lambda err: err.path)
    if errors:
        formatted = "; ".join(error.message for error in errors)
        raise HTTPException(status_code=422, detail=f"Schema validation failed: {formatted}")

    storage_path = Path(os.getenv("AUDIT_LOG_STORAGE_PATH", str(DEFAULT_STORAGE_PATH)))
    _ensure_storage_path(storage_path)

    with storage_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_serialize_event(event)) + "\n")

    logger.info("audit_event_ingested", extra={"event_id": event_id})
    return AuditIngestResponse(event=event)


@app.get("/audit/events/{event_id}", response_model=AuditEventOut)
async def get_event(event_id: str) -> AuditEventOut:
    storage_path = Path(os.getenv("AUDIT_LOG_STORAGE_PATH", str(DEFAULT_STORAGE_PATH)))
    if not storage_path.exists():
        raise HTTPException(status_code=404, detail="No audit events stored")

    with storage_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            data = json.loads(line)
            if data.get("id") == event_id:
                if "timestamp" in data:
                    data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                return AuditEventOut(**data)

    raise HTTPException(status_code=404, detail="Audit event not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
