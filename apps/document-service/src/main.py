from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(REPO_ROOT)

from cryptography.fernet import Fernet  # noqa: E402
from document_policy import evaluate_document_policy  # noqa: E402
from document_storage import DocumentStore  # noqa: E402
from observability.metrics import (  # noqa: E402
    RequestMetricsMiddleware,
    build_kpi_handles,
    configure_metrics,
)
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from security.api_governance import (  # noqa: E402
    apply_api_governance,
    version_response_payload,
)
from security.auth import AuthTenantMiddleware  # noqa: E402
from security.crypto import get_encryption_key  # noqa: E402
from security.dlp import DLPFinding, ensure_dlp_environment, scan_payload  # noqa: E402

from config import validate_startup_config  # noqa: E402
from packages.version import API_VERSION  # noqa: E402

logger = logging.getLogger("document-service")
logging.basicConfig(level=logging.INFO)

validate_startup_config()

app = FastAPI(title="Document Service", version=API_VERSION, openapi_prefix="/v1")
api_router = APIRouter(prefix="/v1")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz", "/health", "/version"})
configure_tracing("document-service")
configure_metrics("document-service")
app.add_middleware(TraceMiddleware, service_name="document-service")
app.add_middleware(RequestMetricsMiddleware, service_name="document-service")
apply_api_governance(app, service_name="document-service")

kpi_handles = build_kpi_handles("document-service")

documents_stored = configure_metrics("document-service").create_counter(
    name="documents_stored_total",
    description="Documents stored in the service",
    unit="1",
)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "document-service"
    dependencies: dict[str, str] = Field(default_factory=dict)


class DocumentRequest(BaseModel):
    name: str
    content: str
    classification: str = Field(..., min_length=1)
    retention_days: int = Field(default=90, ge=1, le=3650)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentResponse(BaseModel):
    document_id: str
    name: str
    classification: str
    retention_days: int
    created_at: datetime
    retention_until: datetime
    metadata: dict[str, Any]
    advisories: list[str] = Field(default_factory=list)


@app.on_event("startup")
async def startup() -> None:
    ensure_dlp_environment()
    encryption_key = get_encryption_key("DOCUMENT_ENCRYPTION_KEY")
    if not encryption_key:
        encryption_key = Fernet.generate_key().decode("utf-8")
        logger.warning("document_encryption_key_generated", extra={"reason": "missing_key"})
    db_path = Path(os.getenv("DOCUMENT_DB_PATH", "apps/document-service/storage/documents.db"))
    app.state.document_store = DocumentStore(db_path, encryption_key=encryption_key)
    logger.info("document_store_ready", extra={"db_path": str(db_path)})


def _get_store(request: Request) -> DocumentStore:
    return request.app.state.document_store


@app.on_event("shutdown")
async def shutdown() -> None:
    logger.info("document_service_shutdown")


@app.get("/health", response_model=HealthResponse)
@app.get("/healthz", response_model=HealthResponse)
async def health(request: Request, response: Response) -> HealthResponse:
    dependencies = {"document_store": "unknown", "dlp_policy": "unknown"}
    try:
        _get_store(request).ping()
        dependencies["document_store"] = "ok"
    except Exception:  # noqa: BLE001
        dependencies["document_store"] = "down"
    try:
        ensure_dlp_environment()
        dependencies["dlp_policy"] = "ok"
    except Exception:  # noqa: BLE001
        dependencies["dlp_policy"] = "down"
    status = "ok" if all(value == "ok" for value in dependencies.values()) else "degraded"
    if status != "ok":
        response.status_code = 503
    return HealthResponse(status=status, dependencies=dependencies)


@app.get("/version")
async def version() -> dict[str, str]:
    return version_response_payload("document-service")


def _build_response(record, advisories: list[str]) -> DocumentResponse:
    return DocumentResponse(
        document_id=record.document_id,
        name=record.name,
        classification=record.classification,
        retention_days=record.retention_days,
        created_at=record.created_at,
        retention_until=record.retention_until,
        metadata=record.metadata,
        advisories=advisories,
    )


def _format_dlp_reasons(findings: list[DLPFinding]) -> list[dict[str, str]]:
    reasons: list[dict[str, str]] = []
    for finding in findings:
        payload = {
            "type": finding.type,
            "severity": finding.severity,
            "field": finding.field,
        }
        if finding.excerpt:
            payload["excerpt"] = finding.excerpt
        reasons.append(payload)
    return reasons


@api_router.post("/documents", response_model=DocumentResponse)
async def create_document(request: Request, payload: DocumentRequest) -> DocumentResponse:
    store = _get_store(request)
    tenant_id = request.state.auth.tenant_id
    dlp_payload = {
        "name": payload.name,
        "content": payload.content,
        "metadata": payload.metadata,
    }
    dlp_result = scan_payload(dlp_payload, classification=payload.classification)
    if dlp_result.decision == "deny":
        kpi_handles.errors.add(1, {"operation": "store_document", "tenant_id": tenant_id})
        logger.warning(
            "document_dlp_blocked",
            extra={"tenant_id": tenant_id, "findings": len(dlp_result.findings)},
        )
        raise HTTPException(
            status_code=403,
            detail={"reasons": _format_dlp_reasons(dlp_result.findings)},
        )
    policy_payload = {
        "document": {
            "classification": payload.classification,
            "retention_days": payload.retention_days,
        }
    }
    decision = evaluate_document_policy(policy_payload)
    if decision.decision == "deny":
        kpi_handles.errors.add(1, {"operation": "store_document", "tenant_id": tenant_id})
        raise HTTPException(status_code=403, detail={"reasons": decision.reasons})

    record = store.create_document(
        tenant_id=tenant_id,
        name=payload.name,
        classification=payload.classification,
        retention_days=payload.retention_days,
        content=payload.content,
        metadata=payload.metadata,
    )
    documents_stored.add(
        1,
        {"classification": payload.classification, "tenant_id": tenant_id},
    )
    kpi_handles.requests.add(1, {"operation": "store_document", "tenant_id": tenant_id})
    advisories = decision.advisories
    if dlp_result.decision == "allow_with_advisory":
        advisories = advisories + dlp_result.advisories
    return _build_response(record, advisories)


@api_router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    request: Request,
    response: Response,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[DocumentResponse]:
    store = _get_store(request)
    tenant_id = request.state.auth.tenant_id
    records = store.list_documents(tenant_id, limit=limit, offset=offset)
    response.headers["X-Total-Count"] = str(store.count_documents(tenant_id))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return [_build_response(record, []) for record in records]


@api_router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, request: Request) -> DocumentResponse:
    store = _get_store(request)
    tenant_id = request.state.auth.tenant_id
    record = store.get_document(tenant_id, document_id)
    if not record:
        kpi_handles.errors.add(1, {"operation": "get_document", "tenant_id": tenant_id})
        raise HTTPException(status_code=404, detail="Document not found")
    kpi_handles.requests.add(1, {"operation": "get_document", "tenant_id": tenant_id})
    return _build_response(record, [])


# ---------------------------------------------------------------------------
# Briefing export endpoints (PDF / PPTX)
# ---------------------------------------------------------------------------

class BriefingExportRequest(BaseModel):
    title: str
    content: str
    sections: list[dict[str, str]] = Field(default_factory=list)
    audience: str = "c_suite"
    generated_at: str = ""
    export_format: str = Field(default="pdf", pattern="^(pdf|pptx)$")
    metadata: dict[str, Any] = Field(default_factory=dict)


class BriefingExportResponse(BaseModel):
    filename: str
    content_base64: str
    content_type: str


@api_router.post("/briefings/export", response_model=BriefingExportResponse)
async def export_briefing(payload: BriefingExportRequest) -> BriefingExportResponse:
    """Render an executive briefing to PDF or PPTX format."""
    from briefing_renderer import render_briefing

    try:
        result = render_briefing(
            title=payload.title,
            content=payload.content,
            sections=payload.sections,
            audience=payload.audience,
            generated_at=payload.generated_at,
            export_format=payload.export_format,
            metadata=payload.metadata,
        )
    except Exception as exc:
        logger.exception("briefing_export_failed")
        raise HTTPException(status_code=500, detail=f"Export failed: {exc}") from exc

    return BriefingExportResponse(
        filename=result["filename"],
        content_base64=result["content_base64"],
        content_type=result["content_type"],
    )


app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
