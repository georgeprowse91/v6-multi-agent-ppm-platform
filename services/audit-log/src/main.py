from __future__ import annotations

import io
import logging
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from azure.core.exceptions import HttpResponseError, ResourceModifiedError
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from jsonschema import Draft202012Validator, FormatChecker

logger = logging.getLogger("audit-log")
logging.basicConfig(level=logging.INFO)

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
_common_src = REPO_ROOT / "packages" / "common" / "src"
if str(_common_src) not in sys.path:
    sys.path.insert(0, str(_common_src))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402
ensure_monorepo_paths(REPO_ROOT)
SCHEMA_PATH = REPO_ROOT / "data" / "schemas" / "audit-event.schema.json"
RETENTION_CONFIG_PATH = REPO_ROOT / "config" / "retention" / "policies.yaml"
CLASSIFICATION_CONFIG_PATH = REPO_ROOT / "config" / "data-classification" / "levels.yaml"

import yaml
from audit_storage import AuditRetentionPolicy, WORMStorageError, get_worm_storage  # noqa: E402
from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from security.api_governance import (  # noqa: E402
    apply_api_governance,
    version_response_payload,
)
from security.auth import AuthTenantMiddleware  # noqa: E402

from packages.version import API_VERSION  # noqa: E402
from security.config import load_yaml  # noqa: E402


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
    dependencies: dict[str, str] = Field(default_factory=dict)


app = FastAPI(title="Audit Log Service", version=API_VERSION, openapi_prefix="/v1")
api_router = APIRouter(prefix="/v1")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz", "/version"})
configure_tracing("audit-log")
configure_metrics("audit-log")
app.add_middleware(TraceMiddleware, service_name="audit-log")
app.add_middleware(RequestMetricsMiddleware, service_name="audit-log")
apply_api_governance(app, service_name="audit-log")


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    dependencies = {"worm_storage": "unknown", "retention_config": "unknown"}
    try:
        get_worm_storage().ping()
        dependencies["worm_storage"] = "ok"
    except (HttpResponseError, OSError, WORMStorageError):
        dependencies["worm_storage"] = "down"
    try:
        load_yaml(RETENTION_CONFIG_PATH)
        dependencies["retention_config"] = "ok"
    except (OSError, ValueError, yaml.YAMLError):
        dependencies["retention_config"] = "down"
    status = "ok" if all(value == "ok" for value in dependencies.values()) else "degraded"
    return HealthResponse(status=status, dependencies=dependencies)


@app.get("/version")
async def version() -> dict[str, str]:
    return version_response_payload("audit-log")


def _serialize_event(event: AuditEventOut) -> dict[str, Any]:
    payload = event.model_dump()
    payload["timestamp"] = event.timestamp.isoformat()
    return payload


def _load_retention_policy(classification: str) -> AuditRetentionPolicy:
    retention_cfg = load_yaml(RETENTION_CONFIG_PATH)
    classification_cfg = load_yaml(CLASSIFICATION_CONFIG_PATH)
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


@api_router.post("/audit/events", response_model=AuditIngestResponse)
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
    except (HttpResponseError, OSError, ResourceModifiedError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    logger.info("audit_event_ingested", extra={"event_id": event_id})
    return AuditIngestResponse(event=event)


@api_router.get("/audit/events/{event_id}", response_model=AuditEventOut)
async def get_event(event_id: str) -> AuditEventOut:
    storage = get_worm_storage()
    data = storage.fetch_event(event_id)
    if data:
        if "timestamp" in data:
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return AuditEventOut(**data)
    raise HTTPException(status_code=404, detail="Audit event not found")


@api_router.get("/audit/evidence/export")
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


app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
