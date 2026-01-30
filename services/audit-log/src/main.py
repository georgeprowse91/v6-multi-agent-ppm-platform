from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
import io
import zipfile
from fastapi import FastAPI, HTTPException, Request
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import BaseModel

logger = logging.getLogger("audit-log")
logging.basicConfig(level=logging.INFO)

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for root in (SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
SCHEMA_PATH = REPO_ROOT / "data" / "schemas" / "audit-event.schema.json"
RETENTION_CONFIG_PATH = REPO_ROOT / "config" / "retention" / "policies.yaml"
CLASSIFICATION_CONFIG_PATH = REPO_ROOT / "config" / "data-classification" / "levels.yaml"

from audit_storage import AuditRetentionPolicy, get_worm_storage  # noqa: E402
from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from security.auth import AuthTenantMiddleware  # noqa: E402
from fastapi.responses import StreamingResponse


def _load_schema() -> dict[str, Any]:
    import json

    return json.loads(SCHEMA_PATH.read_text())


def _validator() -> Draft202012Validator:
    return Draft202012Validator(_load_schema(), format_checker=FormatChecker())


class AuditEventIn(BaseModel):
    id: str
    timestamp: datetime
    tenant_id: str
    actor: dict[str, Any]
    action: str
    resource: dict[str, Any]
    outcome: str
    classification: str
    metadata: dict[str, Any] | None = None
    trace_id: str | None = None
    correlation_id: str | None = None


class AuditEventOut(BaseModel):
    id: str
    timestamp: datetime
    tenant_id: str
    actor: dict[str, Any]
    action: str
    resource: dict[str, Any]
    outcome: str
    classification: str
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
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz"})
configure_tracing("audit-log")
configure_metrics("audit-log")
app.add_middleware(TraceMiddleware, service_name="audit-log")
app.add_middleware(RequestMetricsMiddleware, service_name="audit-log")


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()


def _serialize_event(event: AuditEventOut) -> dict[str, Any]:
    payload = event.model_dump()
    payload["timestamp"] = event.timestamp.isoformat()
    return payload


def _load_retention_policy(classification: str) -> AuditRetentionPolicy:
    retention_cfg = yaml.safe_load(RETENTION_CONFIG_PATH.read_text())
    classification_cfg = yaml.safe_load(CLASSIFICATION_CONFIG_PATH.read_text())
    policy_id = next(
        (
            level.get("retention_policy")
            for level in classification_cfg.get("levels", [])
            if level["id"] == classification
        ),
        None,
    )
    if not policy_id:
        raise HTTPException(status_code=400, detail="Retention policy not configured")
    policy = next((p for p in retention_cfg.get("policies", []) if p["id"] == policy_id), None)
    if not policy:
        raise HTTPException(status_code=400, detail="Retention policy not found")
    return AuditRetentionPolicy(policy_id=policy["id"], duration_days=policy["duration_days"])


@app.post("/audit/events", response_model=AuditIngestResponse)
async def ingest_event(payload: AuditEventIn) -> AuditIngestResponse:
    event_id = payload.id or str(uuid4())
    timestamp = payload.timestamp or datetime.now(timezone.utc)
    event = AuditEventOut(
        id=event_id,
        timestamp=timestamp,
        tenant_id=payload.tenant_id,
        actor=payload.actor,
        action=payload.action,
        resource=payload.resource,
        outcome=payload.outcome,
        classification=payload.classification,
        metadata=payload.metadata,
        trace_id=payload.trace_id,
        correlation_id=payload.correlation_id,
    )

    validator = _validator()
    errors = sorted(validator.iter_errors(_serialize_event(event)), key=lambda err: err.path)
    if errors:
        formatted = "; ".join(error.message for error in errors)
        raise HTTPException(status_code=422, detail=f"Schema validation failed: {formatted}")

    retention_policy = _load_retention_policy(payload.classification)
    storage = get_worm_storage()
    try:
        storage.persist_event(event_id, _serialize_event(event), retention_policy)
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    logger.info("audit_event_ingested", extra={"event_id": event_id})
    return AuditIngestResponse(event=event)


@app.get("/audit/events/{event_id}", response_model=AuditEventOut)
async def get_event(event_id: str) -> AuditEventOut:
    storage = get_worm_storage()
    data = storage.fetch_event(event_id)
    if data:
        if "timestamp" in data:
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return AuditEventOut(**data)
    raise HTTPException(status_code=404, detail="Audit event not found")


@app.get("/audit/evidence/export")
async def export_evidence(request: Request) -> StreamingResponse:
    auth = request.state.auth
    storage = get_worm_storage()
    events = [event for event in storage.list_events() if event.get("tenant_id") == auth.tenant_id]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for event in events:
            event_id = event.get("id", "unknown")
            archive.writestr(f"events/{event_id}.json", yaml.safe_dump(event))
    buffer.seek(0)
    headers = {"X-Event-Count": str(len(events))}
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers=headers,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
