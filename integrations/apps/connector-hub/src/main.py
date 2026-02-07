from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[4]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for root in (REPO_ROOT, SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from packages.version import API_VERSION  # noqa: E402
from connector_storage import ConnectorStore  # noqa: E402
from observability.metrics import (  # noqa: E402
    RequestMetricsMiddleware,
    build_kpi_handles,
    configure_metrics,
)
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from security.auth import AuthTenantMiddleware  # noqa: E402
from security.errors import register_error_handlers  # noqa: E402
from security.headers import SecurityHeadersMiddleware  # noqa: E402

logger = logging.getLogger("connector-hub")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Connector Hub", version=API_VERSION, openapi_prefix="/v1")
api_router = APIRouter(prefix="/v1")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/health", "/healthz", "/version"})
app.add_middleware(SecurityHeadersMiddleware)
configure_tracing("connector-hub")
configure_metrics("connector-hub")
app.add_middleware(TraceMiddleware, service_name="connector-hub")
app.add_middleware(RequestMetricsMiddleware, service_name="connector-hub")
register_error_handlers(app)

store: ConnectorStore | None = None
kpi_handles = build_kpi_handles("connector-hub")

connectors_enabled = configure_metrics("connector-hub").create_counter(
    name="connectors_enabled_total",
    description="Connectors enabled",
    unit="1",
)
connectors_disabled = configure_metrics("connector-hub").create_counter(
    name="connectors_disabled_total",
    description="Connectors disabled",
    unit="1",
)
connector_health_checks = configure_metrics("connector-hub").create_counter(
    name="connector_health_checks_total",
    description="Connector health checks",
    unit="1",
)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "connector-hub"
    dependencies: dict[str, str] = Field(default_factory=dict)


class ConnectorRequest(BaseModel):
    name: str
    version: str
    enabled: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorUpdateRequest(BaseModel):
    version: str | None = None
    enabled: bool | None = None
    health_status: str | None = Field(
        default=None, pattern="^(healthy|degraded|unhealthy|unknown)$"
    )


class ConnectorResponse(BaseModel):
    connector_id: str
    name: str
    version: str
    enabled: bool
    health_status: str
    last_checked: datetime | None
    metadata: dict[str, Any]


@app.on_event("startup")
async def startup() -> None:
    global store
    db_path = Path(os.getenv("CONNECTOR_DB_PATH", "integrations/apps/connector-hub/storage/connectors.db"))
    store = ConnectorStore(db_path)
    logger.info("connector_store_ready", extra={"db_path": str(db_path)})


@app.get("/health", response_model=HealthResponse)
@app.get("/healthz", response_model=HealthResponse)
async def health() -> HealthResponse:
    dependencies = {"connector_store": "unknown"}
    try:
        if store:
            store.ping()
            dependencies["connector_store"] = "ok"
        else:
            dependencies["connector_store"] = "down"
    except Exception:  # noqa: BLE001
        dependencies["connector_store"] = "down"
    status = "ok" if all(value == "ok" for value in dependencies.values()) else "degraded"
    return HealthResponse(status=status, dependencies=dependencies)


@app.get("/version")
async def version() -> dict[str, str]:
    return {
        "service": "connector-hub",
        "api_version": API_VERSION,
        "build_sha": os.getenv("BUILD_SHA", "unknown"),
    }


def _build_response(record) -> ConnectorResponse:
    return ConnectorResponse(
        connector_id=record.connector_id,
        name=record.name,
        version=record.version,
        enabled=record.enabled,
        health_status=record.health_status,
        last_checked=record.last_checked,
        metadata=record.metadata,
    )


@api_router.post("/connectors", response_model=ConnectorResponse)
async def create_connector(request: Request, payload: ConnectorRequest) -> ConnectorResponse:
    assert store is not None
    tenant_id = request.state.auth.tenant_id
    record = store.create_connector(
        tenant_id=tenant_id,
        name=payload.name,
        version=payload.version,
        metadata=payload.metadata,
        enabled=payload.enabled,
    )
    if payload.enabled:
        connectors_enabled.add(1, {"tenant_id": tenant_id})
    else:
        connectors_disabled.add(1, {"tenant_id": tenant_id})
    kpi_handles.requests.add(1, {"operation": "register_connector", "tenant_id": tenant_id})
    return _build_response(record)


@api_router.get("/connectors", response_model=list[ConnectorResponse])
async def list_connectors(
    request: Request,
    response: Response,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[ConnectorResponse]:
    assert store is not None
    tenant_id = request.state.auth.tenant_id
    records = store.list_connectors(tenant_id)
    sliced = records[offset : offset + limit]
    response.headers["X-Total-Count"] = str(len(records))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return [_build_response(record) for record in sliced]


@api_router.patch("/connectors/{connector_id}", response_model=ConnectorResponse)
async def update_connector(
    connector_id: str, request: Request, payload: ConnectorUpdateRequest
) -> ConnectorResponse:
    assert store is not None
    tenant_id = request.state.auth.tenant_id
    record = store.update_connector(
        tenant_id=tenant_id,
        connector_id=connector_id,
        version=payload.version,
        enabled=payload.enabled,
        health_status=payload.health_status,
    )
    if not record:
        kpi_handles.errors.add(1, {"operation": "update_connector", "tenant_id": tenant_id})
        raise HTTPException(status_code=404, detail="Connector not found")
    if payload.enabled is True:
        connectors_enabled.add(1, {"tenant_id": tenant_id})
    if payload.enabled is False:
        connectors_disabled.add(1, {"tenant_id": tenant_id})
    if payload.health_status is not None:
        connector_health_checks.add(1, {"tenant_id": tenant_id, "status": payload.health_status})
    kpi_handles.requests.add(1, {"operation": "update_connector", "tenant_id": tenant_id})
    return _build_response(record)


@api_router.get("/connectors/{connector_id}/health", response_model=ConnectorResponse)
async def connector_health(connector_id: str, request: Request) -> ConnectorResponse:
    assert store is not None
    tenant_id = request.state.auth.tenant_id
    record = store.get_connector(tenant_id, connector_id)
    if not record:
        kpi_handles.errors.add(1, {"operation": "connector_health", "tenant_id": tenant_id})
        raise HTTPException(status_code=404, detail="Connector not found")
    connector_health_checks.add(1, {"tenant_id": tenant_id, "status": record.health_status})
    kpi_handles.requests.add(1, {"operation": "connector_health", "tenant_id": tenant_id})
    return _build_response(record)


app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
