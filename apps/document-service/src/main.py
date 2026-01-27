from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCUMENT_ROOT = Path(__file__).resolve().parent
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for root in (DOCUMENT_ROOT, SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from document_policy import evaluate_document_policy  # noqa: E402
from document_storage import DocumentStore  # noqa: E402
from observability.metrics import (  # noqa: E402
    RequestMetricsMiddleware,
    build_kpi_handles,
    configure_metrics,
)
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from security.auth import AuthTenantMiddleware  # noqa: E402

logger = logging.getLogger("document-service")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Document Service", version="0.1.0")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz", "/health"})
configure_tracing("document-service")
configure_metrics("document-service")
app.add_middleware(TraceMiddleware, service_name="document-service")
app.add_middleware(RequestMetricsMiddleware, service_name="document-service")

store: DocumentStore | None = None
kpi_handles = build_kpi_handles("document-service")

documents_stored = configure_metrics("document-service").create_counter(
    name="documents_stored_total",
    description="Documents stored in the service",
    unit="1",
)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "document-service"


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
    global store
    db_path = Path(os.getenv("DOCUMENT_DB_PATH", "apps/document-service/storage/documents.db"))
    store = DocumentStore(db_path)
    logger.info("document_store_ready", extra={"db_path": str(db_path)})


def _get_store() -> DocumentStore:
    global store
    if store is None:
        db_path = Path(os.getenv("DOCUMENT_DB_PATH", "apps/document-service/storage/documents.db"))
        store = DocumentStore(db_path)
        logger.info("document_store_initialized", extra={"db_path": str(db_path)})
    return store


@app.get("/health", response_model=HealthResponse)
@app.get("/healthz", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


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


@app.post("/documents", response_model=DocumentResponse)
async def create_document(request: Request, payload: DocumentRequest) -> DocumentResponse:
    store = _get_store()
    tenant_id = request.state.auth.tenant_id
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
    return _build_response(record, decision.advisories)


@app.get("/documents", response_model=list[DocumentResponse])
async def list_documents(request: Request) -> list[DocumentResponse]:
    store = _get_store()
    tenant_id = request.state.auth.tenant_id
    records = store.list_documents(tenant_id)
    return [_build_response(record, []) for record in records]


@app.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, request: Request) -> DocumentResponse:
    store = _get_store()
    tenant_id = request.state.auth.tenant_id
    record = store.get_document(tenant_id, document_id)
    if not record:
        kpi_handles.errors.add(1, {"operation": "get_document", "tenant_id": tenant_id})
        raise HTTPException(status_code=404, detail="Document not found")
    kpi_handles.requests.add(1, {"operation": "get_document", "tenant_id": tenant_id})
    return _build_response(record, [])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
