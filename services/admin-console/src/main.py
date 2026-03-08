"""Admin Console – FastAPI application.

Provides operator workflows for managing tenants, agent settings,
connector instances, and platform-level system monitoring.
"""

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

from admin_store import AdminStore  # noqa: E402
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

from config import validate_startup_config  # noqa: E402
from packages.version import API_VERSION  # noqa: E402

logger = logging.getLogger("admin-console")
logging.basicConfig(level=logging.INFO)

validate_startup_config()

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Admin Console", version=API_VERSION, openapi_prefix="/v1")
api_router = APIRouter(prefix="/v1")
app.add_middleware(
    AuthTenantMiddleware,
    exempt_paths={"/health", "/healthz", "/version"},
)
configure_tracing("admin-console")
configure_metrics("admin-console")
app.add_middleware(TraceMiddleware, service_name="admin-console")
app.add_middleware(RequestMetricsMiddleware, service_name="admin-console")
apply_api_governance(app, service_name="admin-console")

kpi_handles = build_kpi_handles("admin-console")

_metrics = configure_metrics("admin-console")
tenants_created = _metrics.create_counter(
    name="tenants_created_total",
    description="Tenants created",
    unit="1",
)
connectors_configured = _metrics.create_counter(
    name="connectors_configured_total",
    description="Connector instances configured",
    unit="1",
)
agent_settings_updated = _metrics.create_counter(
    name="agent_settings_updated_total",
    description="Agent settings updated",
    unit="1",
)
system_events_recorded = _metrics.create_counter(
    name="system_events_recorded_total",
    description="System events recorded",
    unit="1",
)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "admin-console"
    dependencies: dict[str, str] = Field(default_factory=dict)


# -- Tenant models --


class TenantCreateRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=256)
    environment: str = Field(default="development", pattern="^(development|dev|staging|production)$")
    settings: dict[str, Any] = Field(default_factory=dict)


class TenantUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=256)
    environment: str | None = Field(
        default=None, pattern="^(development|dev|staging|production)$"
    )
    settings: dict[str, Any] | None = None


class TenantResponse(BaseModel):
    tenant_id: str
    display_name: str
    environment: str
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime


# -- Connector instance models --


class ConnectorInstanceCreateRequest(BaseModel):
    connector_type: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=256)
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class ConnectorInstanceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    enabled: bool | None = None
    config: dict[str, Any] | None = None
    health_status: str | None = Field(
        default=None, pattern="^(healthy|degraded|unhealthy|unknown)$"
    )


class ConnectorInstanceResponse(BaseModel):
    instance_id: str
    tenant_id: str
    connector_type: str
    name: str
    enabled: bool
    config: dict[str, Any]
    health_status: str
    last_synced: datetime | None
    created_at: datetime
    updated_at: datetime


# -- Agent setting models --


class AgentSettingRequest(BaseModel):
    enabled: bool = True
    parameters: dict[str, Any] = Field(default_factory=dict)
    updated_by: str | None = None


class AgentSettingResponse(BaseModel):
    setting_id: str
    tenant_id: str
    agent_id: str
    enabled: bool
    parameters: dict[str, Any]
    updated_at: datetime
    updated_by: str | None


# -- System monitoring models --


class SystemEventCreateRequest(BaseModel):
    event_type: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    severity: str = Field(default="info", pattern="^(debug|info|warning|error|critical)$")
    metadata: dict[str, Any] = Field(default_factory=dict)


class SystemEventResponse(BaseModel):
    event_id: str
    tenant_id: str
    event_type: str
    source: str
    severity: str
    message: str
    metadata: dict[str, Any]
    created_at: datetime


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def startup() -> None:
    db_path = Path(os.getenv("ADMIN_DB_PATH", "services/admin-console/storage/admin.db"))
    app.state.admin_store = AdminStore(db_path)
    logger.info("admin_store_ready", extra={"db_path": str(db_path)})


@app.on_event("shutdown")
async def shutdown() -> None:
    logger.info("admin_console_shutdown")


def _get_store(request: Request) -> AdminStore:
    return request.app.state.admin_store


# ---------------------------------------------------------------------------
# Health / version
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
@app.get("/healthz", response_model=HealthResponse)
async def health(request: Request, response: Response) -> HealthResponse:
    dependencies: dict[str, str] = {"admin_store": "unknown"}
    try:
        _get_store(request).ping()
        dependencies["admin_store"] = "ok"
    except Exception:  # noqa: BLE001
        dependencies["admin_store"] = "down"
    status = "ok" if all(v == "ok" for v in dependencies.values()) else "degraded"
    if status != "ok":
        response.status_code = 503
    return HealthResponse(status=status, dependencies=dependencies)


@app.get("/version")
async def version() -> dict[str, str]:
    return version_response_payload("admin-console")


# ---------------------------------------------------------------------------
# Tenant configuration
# ---------------------------------------------------------------------------


@api_router.post("/tenants", response_model=TenantResponse, status_code=201)
async def create_tenant(request: Request, payload: TenantCreateRequest) -> TenantResponse:
    store = _get_store(request)
    existing = store.get_tenant(payload.tenant_id)
    if existing:
        raise HTTPException(status_code=409, detail="Tenant already exists")
    record = store.create_tenant(
        tenant_id=payload.tenant_id,
        display_name=payload.display_name,
        environment=payload.environment,
        settings=payload.settings,
    )
    tenants_created.add(1, {"tenant_id": payload.tenant_id})
    kpi_handles.requests.add(1, {"operation": "create_tenant"})
    logger.info("tenant_created", extra={"tenant_id": payload.tenant_id})
    return _tenant_response(record)


@api_router.get("/tenants", response_model=list[TenantResponse])
async def list_tenants(
    request: Request,
    response: Response,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[TenantResponse]:
    store = _get_store(request)
    tenants = store.list_tenants()
    response.headers["X-Total-Count"] = str(len(tenants))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    sliced = tenants[offset : offset + limit]
    return [_tenant_response(t) for t in sliced]


@api_router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: str, request: Request) -> TenantResponse:
    store = _get_store(request)
    record = store.get_tenant(tenant_id)
    if not record:
        kpi_handles.errors.add(1, {"operation": "get_tenant"})
        raise HTTPException(status_code=404, detail="Tenant not found")
    return _tenant_response(record)


@api_router.patch("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str, request: Request, payload: TenantUpdateRequest
) -> TenantResponse:
    store = _get_store(request)
    record = store.update_tenant(
        tenant_id=tenant_id,
        display_name=payload.display_name,
        environment=payload.environment,
        settings=payload.settings,
    )
    if not record:
        kpi_handles.errors.add(1, {"operation": "update_tenant"})
        raise HTTPException(status_code=404, detail="Tenant not found")
    kpi_handles.requests.add(1, {"operation": "update_tenant"})
    return _tenant_response(record)


@api_router.delete("/tenants/{tenant_id}", status_code=204)
async def delete_tenant(tenant_id: str, request: Request) -> Response:
    store = _get_store(request)
    deleted = store.delete_tenant(tenant_id)
    if not deleted:
        kpi_handles.errors.add(1, {"operation": "delete_tenant"})
        raise HTTPException(status_code=404, detail="Tenant not found")
    kpi_handles.requests.add(1, {"operation": "delete_tenant"})
    logger.info("tenant_deleted", extra={"tenant_id": tenant_id})
    return Response(status_code=204)


def _tenant_response(record) -> TenantResponse:
    return TenantResponse(
        tenant_id=record.tenant_id,
        display_name=record.display_name,
        environment=record.environment,
        settings=record.settings,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


# ---------------------------------------------------------------------------
# Connector instances
# ---------------------------------------------------------------------------


@api_router.post(
    "/connectors/instances", response_model=ConnectorInstanceResponse, status_code=201
)
async def create_connector_instance(
    request: Request, payload: ConnectorInstanceCreateRequest
) -> ConnectorInstanceResponse:
    store = _get_store(request)
    tenant_id = request.state.auth.tenant_id
    record = store.create_connector_instance(
        tenant_id=tenant_id,
        connector_type=payload.connector_type,
        name=payload.name,
        config=payload.config,
        enabled=payload.enabled,
    )
    connectors_configured.add(1, {"tenant_id": tenant_id, "type": payload.connector_type})
    kpi_handles.requests.add(1, {"operation": "create_connector_instance", "tenant_id": tenant_id})
    logger.info(
        "connector_instance_created",
        extra={"tenant_id": tenant_id, "instance_id": record.instance_id},
    )
    return _connector_response(record)


@api_router.get("/connectors/instances", response_model=list[ConnectorInstanceResponse])
async def list_connector_instances(
    request: Request,
    response: Response,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[ConnectorInstanceResponse]:
    store = _get_store(request)
    tenant_id = request.state.auth.tenant_id
    records = store.list_connector_instances(tenant_id)
    response.headers["X-Total-Count"] = str(len(records))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    sliced = records[offset : offset + limit]
    return [_connector_response(r) for r in sliced]


@api_router.get(
    "/connectors/instances/{instance_id}", response_model=ConnectorInstanceResponse
)
async def get_connector_instance(
    instance_id: str, request: Request
) -> ConnectorInstanceResponse:
    store = _get_store(request)
    tenant_id = request.state.auth.tenant_id
    record = store.get_connector_instance(tenant_id, instance_id)
    if not record:
        kpi_handles.errors.add(
            1, {"operation": "get_connector_instance", "tenant_id": tenant_id}
        )
        raise HTTPException(status_code=404, detail="Connector instance not found")
    return _connector_response(record)


@api_router.patch(
    "/connectors/instances/{instance_id}", response_model=ConnectorInstanceResponse
)
async def update_connector_instance(
    instance_id: str,
    request: Request,
    payload: ConnectorInstanceUpdateRequest,
) -> ConnectorInstanceResponse:
    store = _get_store(request)
    tenant_id = request.state.auth.tenant_id
    record = store.update_connector_instance(
        tenant_id=tenant_id,
        instance_id=instance_id,
        name=payload.name,
        enabled=payload.enabled,
        config=payload.config,
        health_status=payload.health_status,
    )
    if not record:
        kpi_handles.errors.add(
            1, {"operation": "update_connector_instance", "tenant_id": tenant_id}
        )
        raise HTTPException(status_code=404, detail="Connector instance not found")
    connectors_configured.add(1, {"tenant_id": tenant_id, "type": record.connector_type})
    kpi_handles.requests.add(
        1, {"operation": "update_connector_instance", "tenant_id": tenant_id}
    )
    return _connector_response(record)


@api_router.delete("/connectors/instances/{instance_id}", status_code=204)
async def delete_connector_instance(instance_id: str, request: Request) -> Response:
    store = _get_store(request)
    tenant_id = request.state.auth.tenant_id
    deleted = store.delete_connector_instance(tenant_id, instance_id)
    if not deleted:
        kpi_handles.errors.add(
            1, {"operation": "delete_connector_instance", "tenant_id": tenant_id}
        )
        raise HTTPException(status_code=404, detail="Connector instance not found")
    kpi_handles.requests.add(
        1, {"operation": "delete_connector_instance", "tenant_id": tenant_id}
    )
    logger.info(
        "connector_instance_deleted",
        extra={"tenant_id": tenant_id, "instance_id": instance_id},
    )
    return Response(status_code=204)


def _connector_response(record) -> ConnectorInstanceResponse:
    return ConnectorInstanceResponse(
        instance_id=record.instance_id,
        tenant_id=record.tenant_id,
        connector_type=record.connector_type,
        name=record.name,
        enabled=record.enabled,
        config=record.config,
        health_status=record.health_status,
        last_synced=record.last_synced,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


# ---------------------------------------------------------------------------
# Agent settings
# ---------------------------------------------------------------------------


@api_router.put("/agents/{agent_id}/settings", response_model=AgentSettingResponse)
async def upsert_agent_setting(
    agent_id: str, request: Request, payload: AgentSettingRequest
) -> AgentSettingResponse:
    store = _get_store(request)
    tenant_id = request.state.auth.tenant_id
    record = store.upsert_agent_setting(
        tenant_id=tenant_id,
        agent_id=agent_id,
        enabled=payload.enabled,
        parameters=payload.parameters,
        updated_by=payload.updated_by,
    )
    agent_settings_updated.add(1, {"tenant_id": tenant_id, "agent_id": agent_id})
    kpi_handles.requests.add(
        1, {"operation": "upsert_agent_setting", "tenant_id": tenant_id}
    )
    logger.info(
        "agent_setting_upserted",
        extra={"tenant_id": tenant_id, "agent_id": agent_id},
    )
    return _agent_setting_response(record)


@api_router.get("/agents/settings", response_model=list[AgentSettingResponse])
async def list_agent_settings(request: Request) -> list[AgentSettingResponse]:
    store = _get_store(request)
    tenant_id = request.state.auth.tenant_id
    records = store.list_agent_settings(tenant_id)
    return [_agent_setting_response(r) for r in records]


@api_router.get("/agents/{agent_id}/settings", response_model=AgentSettingResponse)
async def get_agent_setting(agent_id: str, request: Request) -> AgentSettingResponse:
    store = _get_store(request)
    tenant_id = request.state.auth.tenant_id
    record = store.get_agent_setting(tenant_id, agent_id)
    if not record:
        kpi_handles.errors.add(
            1, {"operation": "get_agent_setting", "tenant_id": tenant_id}
        )
        raise HTTPException(status_code=404, detail="Agent setting not found")
    return _agent_setting_response(record)


@api_router.delete("/agents/{agent_id}/settings", status_code=204)
async def delete_agent_setting(agent_id: str, request: Request) -> Response:
    store = _get_store(request)
    tenant_id = request.state.auth.tenant_id
    deleted = store.delete_agent_setting(tenant_id, agent_id)
    if not deleted:
        kpi_handles.errors.add(
            1, {"operation": "delete_agent_setting", "tenant_id": tenant_id}
        )
        raise HTTPException(status_code=404, detail="Agent setting not found")
    kpi_handles.requests.add(
        1, {"operation": "delete_agent_setting", "tenant_id": tenant_id}
    )
    return Response(status_code=204)


def _agent_setting_response(record) -> AgentSettingResponse:
    return AgentSettingResponse(
        setting_id=record.setting_id,
        tenant_id=record.tenant_id,
        agent_id=record.agent_id,
        enabled=record.enabled,
        parameters=record.parameters,
        updated_at=record.updated_at,
        updated_by=record.updated_by,
    )


# ---------------------------------------------------------------------------
# System monitoring
# ---------------------------------------------------------------------------


@api_router.post("/monitoring/events", response_model=SystemEventResponse, status_code=201)
async def create_system_event(
    request: Request, payload: SystemEventCreateRequest
) -> SystemEventResponse:
    store = _get_store(request)
    tenant_id = request.state.auth.tenant_id
    record = store.record_event(
        tenant_id=tenant_id,
        event_type=payload.event_type,
        source=payload.source,
        message=payload.message,
        severity=payload.severity,
        metadata=payload.metadata,
    )
    system_events_recorded.add(
        1, {"tenant_id": tenant_id, "event_type": payload.event_type}
    )
    kpi_handles.requests.add(
        1, {"operation": "create_system_event", "tenant_id": tenant_id}
    )
    return _event_response(record)


@api_router.get("/monitoring/events", response_model=list[SystemEventResponse])
async def list_system_events(
    request: Request,
    response: Response,
    event_type: str | None = Query(None),
    severity: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[SystemEventResponse]:
    store = _get_store(request)
    tenant_id = request.state.auth.tenant_id
    total = store.count_events(tenant_id, event_type=event_type, severity=severity)
    records = store.list_events(
        tenant_id, event_type=event_type, severity=severity, limit=limit, offset=offset
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return [_event_response(r) for r in records]


@api_router.get("/monitoring/summary")
async def monitoring_summary(request: Request) -> dict[str, Any]:
    """Return an overview of system health across all monitored dimensions."""
    store = _get_store(request)
    tenant_id = request.state.auth.tenant_id
    connectors = store.list_connector_instances(tenant_id)
    agents = store.list_agent_settings(tenant_id)
    event_counts = {
        "total": store.count_events(tenant_id),
        "errors": store.count_events(tenant_id, severity="error"),
        "warnings": store.count_events(tenant_id, severity="warning"),
        "critical": store.count_events(tenant_id, severity="critical"),
    }
    connector_health = {
        "total": len(connectors),
        "healthy": sum(1 for c in connectors if c.health_status == "healthy"),
        "degraded": sum(1 for c in connectors if c.health_status == "degraded"),
        "unhealthy": sum(1 for c in connectors if c.health_status == "unhealthy"),
        "unknown": sum(1 for c in connectors if c.health_status == "unknown"),
    }
    agent_overview = {
        "total": len(agents),
        "enabled": sum(1 for a in agents if a.enabled),
        "disabled": sum(1 for a in agents if not a.enabled),
    }
    return {
        "tenant_id": tenant_id,
        "connectors": connector_health,
        "agents": agent_overview,
        "events": event_counts,
    }


def _event_response(record) -> SystemEventResponse:
    return SystemEventResponse(
        event_id=record.event_id,
        tenant_id=record.tenant_id,
        event_type=record.event_type,
        source=record.source,
        severity=record.severity,
        message=record.message,
        metadata=record.metadata,
        created_at=record.created_at,
    )


# ---------------------------------------------------------------------------
# Mount router and main entry point
# ---------------------------------------------------------------------------

app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
