from __future__ import annotations

import importlib
import inspect
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

REPO_ROOT = Path(__file__).resolve().parents[3]

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(REPO_ROOT)

from common.env_validation import (  # noqa: E402
    durability_mode_for_storage,
    enforce_no_default_file_backed_storage,
    environment_value,
    reject_placeholder_secrets,
)
from feature_flags import is_feature_enabled  # noqa: E402
from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from retention_scheduler import RetentionScheduler  # noqa: E402
from schema_compatibility import CompatibilityMode, validate_compatibility  # noqa: E402
from security.api_governance import (  # noqa: E402
    apply_api_governance,
    version_response_payload,
)
from security.auth import AuthTenantMiddleware  # noqa: E402
from security.config import load_yaml  # noqa: E402
from storage import (  # noqa: E402
    DataServiceStore,
    EntityRecord,
    SchemaExistsError,
    SchemaRecord,
    to_async_database_url,
)

from packages.version import API_VERSION

logger = logging.getLogger("data-service")
logging.basicConfig(level=logging.INFO)

SCHEMA_DIR = REPO_ROOT / "data" / "schemas"


class HealthResponse(BaseModel):
    status: str
    checks: dict[str, dict[str, str]] = Field(default_factory=dict)
    severity: str
    remediation_hint: str
    observed_at: str
    degraded_since: str | None = None
    recovered_at: str | None = None


class SchemaRegistrationRequest(BaseModel):
    name: str = Field(..., description="Canonical schema name")
    schema: dict[str, Any] = Field(..., description="JSON Schema payload")
    version: int | None = Field(None, description="Optional schema version override")
    compatibility_mode: CompatibilityMode = Field(
        "full",
        description=(
            "Compatibility validation mode against latest version: " "backward, forward, or full"
        ),
    )


class SchemaResponse(BaseModel):
    name: str
    version: int
    schema: dict[str, Any]
    created_at: datetime


class SchemaSummaryResponse(BaseModel):
    name: str
    latest_version: int
    versions: int


class SchemaPromotionRequest(BaseModel):
    environment: str


class SchemaPromotionResponse(BaseModel):
    name: str
    version: int
    environment: str
    promoted_at: datetime


class EntityIngestRequest(BaseModel):
    tenant_id: str
    data: dict[str, Any]
    schema_version: int | None = None
    entity_id: str | None = None
    connector_name: str | None = None


class EntityResponse(BaseModel):
    id: str
    tenant_id: str
    schema_name: str
    schema_version: int
    data: dict[str, Any]
    created_at: datetime
    updated_at: datetime


AGENT_RUN_SCHEMA = "agent-run"
SCENARIO_SCHEMA = "scenario"


class ScenarioIngestRequest(BaseModel):
    tenant_id: str
    data: dict[str, Any]
    schema_version: int | None = None
    scenario_id: str | None = None


class ConnectorIngestRequest(BaseModel):
    connector_name: str
    tenant_id: str
    fixture_path: str | None = None
    live: bool = False


class ConnectorIngestResponse(BaseModel):
    connector_name: str
    tenant_id: str
    total_records: int
    schemas: dict[str, int]
    ingested_at: datetime


class RetentionStatusResponse(BaseModel):
    interval_seconds: int
    retention_days: int
    last_pruned_at: str | None
    last_pruned_count: int


reject_placeholder_secrets(
    service_name="data-service",
    environment=os.getenv("ENVIRONMENT"),
    secret_vars={
        k: v
        for k, v in {
            "DATABASE_URL": os.getenv("DATA_SERVICE_DATABASE_URL") or os.getenv("DATABASE_URL", ""),
        }.items()
        if v
    },
)

app = FastAPI(title="Data Service", version=API_VERSION, openapi_prefix="/v1")
api_router = APIRouter(prefix="/v1")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz", "/version"})
configure_tracing("data-service")
configure_metrics("data-service")
app.add_middleware(TraceMiddleware, service_name="data-service")
app.add_middleware(RequestMetricsMiddleware, service_name="data-service")
apply_api_governance(app, service_name="data-service")
meter = configure_metrics("data-service")
READINESS_DEGRADED_TOTAL = meter.create_counter(
    name="service_readiness_degraded_total",
    description="Total number of readiness degradation transitions.",
    unit="1",
)
READINESS_RECOVERY_TOTAL = meter.create_counter(
    name="service_readiness_recovered_total",
    description="Total number of readiness recovery transitions.",
    unit="1",
)
READINESS_MTTR_SECONDS = meter.create_histogram(
    name="service_readiness_mttr_seconds",
    description="Readiness mean-time-to-recovery samples in seconds.",
    unit="s",
)
app.state.readiness_state = {
    "last_status": "ok",
    "degraded_since": None,
    "recovered_at": None,
}


@app.on_event("startup")
async def startup() -> None:
    selected_database_url = os.getenv("DATA_SERVICE_DATABASE_URL") or os.getenv("DATABASE_URL")
    used_default_database = not selected_database_url
    if used_default_database:
        selected_database_url = "sqlite+aiosqlite:///data/data_service.db"

    environment = environment_value(os.environ)
    enforce_no_default_file_backed_storage(
        service_name="data-service",
        setting_names=("DATA_SERVICE_DATABASE_URL", "DATABASE_URL"),
        selected_value=selected_database_url,
        used_default=used_default_database,
        environment=environment,
        remediation_hint=(
            "Configure a persistent database DSN (for example PostgreSQL) "
            "through DATA_SERVICE_DATABASE_URL or DATABASE_URL."
        ),
    )

    database_url = to_async_database_url(selected_database_url)
    logger.info(
        "data-service persistence configuration",
        extra={
            "environment": environment,
            "storage_backend": "sqlite" if "sqlite" in database_url else "sql",
            "durability_mode": durability_mode_for_storage(database_url),
            "database_url_source": "default" if used_default_database else "explicit",
        },
    )

    store = DataServiceStore(database_url)
    await store.initialize()
    if os.getenv("DATA_SERVICE_LOAD_SEED_SCHEMAS", "true").lower() in {"true", "1", "yes"}:
        seeded = await store.seed_schemas(SCHEMA_DIR)
        logger.info("seed_schemas", extra={"count": seeded})
    app.state.store = store
    interval = int(os.getenv("DATA_SERVICE_RETENTION_INTERVAL_SECONDS", "3600"))
    retention_days = int(os.getenv("DATA_SERVICE_RETENTION_DAYS", "365"))
    scheduler = RetentionScheduler(store, interval_seconds=interval, retention_days=retention_days)
    scheduler.start()
    app.state.retention_scheduler = scheduler


@app.on_event("shutdown")
async def shutdown() -> None:
    scheduler = get_retention_scheduler()
    if scheduler:
        scheduler.stop()


def get_store() -> DataServiceStore:
    return app.state.store


def get_retention_scheduler() -> RetentionScheduler | None:
    return getattr(app.state, "retention_scheduler", None)


def _observed_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_check(status: str, severity: str, remediation_hint: str) -> dict[str, str]:
    return {
        "status": status,
        "severity": severity,
        "remediation_hint": remediation_hint,
        "observed_at": _observed_at(),
    }


def _scheduler_heartbeat_fresh(snapshot: dict[str, str | int]) -> bool:
    heartbeat_at = str(snapshot.get("last_heartbeat_at") or "")
    if not heartbeat_at:
        return False
    heartbeat = datetime.fromisoformat(heartbeat_at)
    interval_seconds = int(snapshot.get("interval_seconds") or 0)
    tolerance = max(5, interval_seconds * 2)
    return (datetime.now(timezone.utc) - heartbeat).total_seconds() <= tolerance


def _update_readiness_metrics(status: str) -> tuple[str | None, str | None]:
    state = app.state.readiness_state
    previous = state["last_status"]
    now = datetime.now(timezone.utc)
    if status != "ok" and previous == "ok":
        state["degraded_since"] = now
        READINESS_DEGRADED_TOTAL.add(1, {"service.name": "data-service"})
    if status == "ok" and previous != "ok":
        degraded_since = state.get("degraded_since")
        if degraded_since:
            READINESS_MTTR_SECONDS.record(
                (now - degraded_since).total_seconds(), {"service.name": "data-service"}
            )
        state["recovered_at"] = now
        state["degraded_since"] = None
        READINESS_RECOVERY_TOTAL.add(1, {"service.name": "data-service"})
    state["last_status"] = status
    degraded_since = state.get("degraded_since")
    recovered_at = state.get("recovered_at")
    return (
        degraded_since.isoformat() if degraded_since else None,
        recovered_at.isoformat() if recovered_at else None,
    )


def _to_response(checks: dict[str, dict[str, str]], status_code: int) -> JSONResponse:
    has_critical = any(item["severity"] == "critical" for item in checks.values())
    status = "ok" if all(item["status"] == "ok" for item in checks.values()) else "degraded"
    severity = "info" if status == "ok" else ("critical" if has_critical else "warning")
    remediation_hint = "; ".join(
        sorted({item["remediation_hint"] for item in checks.values() if item["remediation_hint"]})
    )
    degraded_since, recovered_at = _update_readiness_metrics(status)
    payload = HealthResponse(
        status=status,
        checks=checks,
        severity=severity,
        remediation_hint=remediation_hint,
        observed_at=_observed_at(),
        degraded_since=degraded_since,
        recovered_at=recovered_at,
    )
    return JSONResponse(
        status_code=status_code if status != "ok" else 200, content=payload.model_dump()
    )


@app.get("/livez", response_model=HealthResponse)
async def livez() -> HealthResponse:
    checks = {"process": _build_check("ok", "info", "")}
    return HealthResponse(
        status="ok",
        checks=checks,
        severity="info",
        remediation_hint="",
        observed_at=_observed_at(),
    )


@app.get("/readyz", response_model=HealthResponse)
async def readyz() -> JSONResponse:
    store = get_store()
    scheduler = get_retention_scheduler()
    checks = {
        "database_transaction_probe": _build_check("ok", "info", ""),
        "retention_scheduler_heartbeat": _build_check("ok", "info", ""),
    }
    try:
        await store.readiness_probe_transaction()
    except (SQLAlchemyError, RuntimeError):
        checks["database_transaction_probe"] = _build_check(
            "down",
            "critical",
            "Verify write/read/delete transaction path for canonical_entities and database connectivity.",
        )
    if not scheduler:
        checks["retention_scheduler_heartbeat"] = _build_check(
            "down",
            "warning",
            "Ensure retention scheduler starts successfully during application startup.",
        )
    else:
        snapshot = scheduler.snapshot()
        if not _scheduler_heartbeat_fresh(snapshot):
            checks["retention_scheduler_heartbeat"] = _build_check(
                "down",
                "warning",
                "Investigate retention scheduler thread and ensure heartbeat updates within expected interval.",
            )
    return _to_response(checks, status_code=503)


@app.get("/readyz/deep", response_model=HealthResponse)
async def deep_readyz() -> JSONResponse:
    store = get_store()
    checks = {"database_transaction_probe": _build_check("ok", "info", "")}
    try:
        await store.readiness_probe_transaction()
    except (SQLAlchemyError, RuntimeError):
        checks["database_transaction_probe"] = _build_check(
            "down",
            "critical",
            "Restore transactional read/write path on canonical_entities and validate connection pool health.",
        )
    return _to_response(checks, status_code=503)


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> JSONResponse:
    return await readyz()


@app.get("/version")
async def version() -> dict[str, str]:
    return version_response_payload("data-service")


@api_router.get("/retention/status", response_model=RetentionStatusResponse)
async def retention_status() -> RetentionStatusResponse:
    scheduler = get_retention_scheduler()
    if not scheduler:
        raise HTTPException(status_code=404, detail="Retention scheduler not configured")
    snapshot = scheduler.snapshot()
    return RetentionStatusResponse(
        interval_seconds=int(snapshot["interval_seconds"]),
        retention_days=int(snapshot["retention_days"]),
        last_pruned_at=snapshot.get("last_pruned_at") or None,
        last_pruned_count=int(snapshot["last_pruned_count"]),
    )


@api_router.post("/schemas", response_model=SchemaResponse)
async def register_schema(
    request: SchemaRegistrationRequest, store: DataServiceStore = Depends(get_store)
) -> SchemaResponse:
    _validate_schema_definition(request.schema)

    latest = await store.get_latest_schema(request.name)
    if latest:
        try:
            validate_compatibility(latest.schema, request.schema, request.compatibility_mode)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        record = await store.register_schema(request.name, request.schema, request.version)
    except SchemaExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return _schema_response(record)


@api_router.get("/schemas", response_model=list[SchemaSummaryResponse])
async def list_schemas(
    response: Response,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    store: DataServiceStore = Depends(get_store),
) -> list[SchemaSummaryResponse]:
    summaries = await store.list_schema_summaries()
    sliced, total = _paginate(summaries, offset=offset, limit=limit)
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return [SchemaSummaryResponse(**summary.__dict__) for summary in sliced]


@api_router.get("/schemas/{schema_name}/versions", response_model=list[SchemaResponse])
async def list_schema_versions(
    schema_name: str,
    response: Response,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    store: DataServiceStore = Depends(get_store),
) -> list[SchemaResponse]:
    records = await store.list_schema_versions(schema_name)
    sliced, total = _paginate(records, offset=offset, limit=limit)
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return [_schema_response(record) for record in sliced]


@api_router.get("/schemas/{schema_name}/latest", response_model=SchemaResponse)
async def get_latest_schema(
    schema_name: str, store: DataServiceStore = Depends(get_store)
) -> SchemaResponse:
    record = await store.get_latest_schema(schema_name)
    if not record:
        raise HTTPException(status_code=404, detail="Schema not found")
    return _schema_response(record)


@api_router.get("/schemas/{schema_name}/versions/{version}", response_model=SchemaResponse)
async def get_schema_version(
    schema_name: str, version: int, store: DataServiceStore = Depends(get_store)
) -> SchemaResponse:
    record = await store.get_schema(schema_name, version)
    if not record:
        raise HTTPException(status_code=404, detail="Schema not found")
    return _schema_response(record)


@api_router.get("/schemas/{schema_name}/promotions", response_model=list[SchemaPromotionResponse])
async def list_schema_promotions(
    schema_name: str,
    response: Response,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    store: DataServiceStore = Depends(get_store),
) -> list[SchemaPromotionResponse]:
    _require_feature("schema_promotions")
    promotions = await store.list_schema_promotions(schema_name)
    sliced, total = _paginate(promotions, offset=offset, limit=limit)
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return [SchemaPromotionResponse(**promo.__dict__) for promo in sliced]


@api_router.post(
    "/schemas/{schema_name}/versions/{version}/promote",
    response_model=SchemaPromotionResponse,
)
async def promote_schema_version(
    schema_name: str,
    version: int,
    request: SchemaPromotionRequest,
    store: DataServiceStore = Depends(get_store),
) -> SchemaPromotionResponse:
    _require_feature("schema_promotions")
    record = await store.get_schema(schema_name, version)
    if not record:
        raise HTTPException(status_code=404, detail="Schema version not found")
    promotion = await store.promote_schema(schema_name, version, request.environment)
    return SchemaPromotionResponse(**promotion.__dict__)


@api_router.post("/entities/{schema_name}", response_model=EntityResponse)
async def ingest_entity(
    schema_name: str,
    request: EntityIngestRequest,
    store: DataServiceStore = Depends(get_store),
) -> EntityResponse:
    record = await _resolve_schema(schema_name, request.schema_version, store)
    await _require_schema_promotion_for_environment(record, store)
    _validate_payload(record, request.data)
    if _canonical_propagation_enabled() and request.connector_name:
        _validate_against_canonical_mapping(schema_name, request.data, request.connector_name)
    entity_id = request.entity_id or request.data.get("id") or str(uuid4())
    stored = await store.store_entity(
        entity_id=entity_id,
        tenant_id=request.tenant_id,
        schema_name=schema_name,
        schema_version=record.version,
        payload=request.data,
    )
    return _entity_response(stored)


@api_router.post("/agent-runs", response_model=EntityResponse)
async def ingest_agent_run(
    request: EntityIngestRequest,
    store: DataServiceStore = Depends(get_store),
) -> EntityResponse:
    _require_feature("agent_run_tracking")
    record = await _resolve_schema(AGENT_RUN_SCHEMA, request.schema_version, store)
    await _require_schema_promotion_for_environment(record, store)
    _validate_payload(record, request.data)
    entity_id = request.entity_id or request.data.get("id") or str(uuid4())
    stored = await store.store_entity(
        entity_id=entity_id,
        tenant_id=request.tenant_id,
        schema_name=AGENT_RUN_SCHEMA,
        schema_version=record.version,
        payload=request.data,
    )
    return _entity_response(stored)


@api_router.post("/scenarios", response_model=EntityResponse)
async def ingest_scenario(
    request: ScenarioIngestRequest,
    store: DataServiceStore = Depends(get_store),
) -> EntityResponse:
    record = await _resolve_schema(SCENARIO_SCHEMA, request.schema_version, store)
    await _require_schema_promotion_for_environment(record, store)
    _validate_payload(record, request.data)
    scenario_id = request.scenario_id or request.data.get("id") or str(uuid4())
    stored = await store.store_entity(
        entity_id=scenario_id,
        tenant_id=request.tenant_id,
        schema_name=SCENARIO_SCHEMA,
        schema_version=record.version,
        payload=request.data,
    )
    return _entity_response(stored)


@api_router.get("/entities/{schema_name}/{entity_id}", response_model=EntityResponse)
async def get_entity(
    schema_name: str, entity_id: str, store: DataServiceStore = Depends(get_store)
) -> EntityResponse:
    record = await store.get_entity(schema_name, entity_id)
    if not record:
        raise HTTPException(status_code=404, detail="Entity not found")
    return _entity_response(record)


@api_router.get("/scenarios/{scenario_id}", response_model=EntityResponse)
async def get_scenario(
    scenario_id: str, store: DataServiceStore = Depends(get_store)
) -> EntityResponse:
    record = await store.get_entity(SCENARIO_SCHEMA, scenario_id)
    if not record:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return _entity_response(record)


@api_router.get("/agent-runs/{agent_run_id}", response_model=EntityResponse)
async def get_agent_run(
    agent_run_id: str, store: DataServiceStore = Depends(get_store)
) -> EntityResponse:
    _require_feature("agent_run_tracking")
    record = await store.get_entity(AGENT_RUN_SCHEMA, agent_run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return _entity_response(record)


class EntitySearchRequest(BaseModel):
    query: str = Field("", description="Full-text search query across entity payload fields")
    filters: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Faceted filters: field name -> list of accepted values",
    )
    sort_by: str = Field("updated_at", description="Field to sort by")
    sort_order: str = Field("desc", description="Sort order: asc or desc")


class FacetBucket(BaseModel):
    value: str
    count: int


class FacetResponse(BaseModel):
    field: str
    buckets: list[FacetBucket]


class EntitySearchResponse(BaseModel):
    items: list[EntityResponse]
    total: int
    offset: int
    limit: int
    facets: list[FacetResponse]


@api_router.get("/entities/{schema_name}", response_model=list[EntityResponse])
async def list_entities(
    schema_name: str,
    response: Response,
    tenant_id: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    store: DataServiceStore = Depends(get_store),
) -> list[EntityResponse]:
    records = await store.list_entities(schema_name, tenant_id, skip, limit)
    response.headers["X-Total-Count"] = str(await store.count_entities(schema_name, tenant_id))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(skip)
    return [_entity_response(record) for record in records]


@api_router.post(
    "/entities/{schema_name}/search",
    response_model=EntitySearchResponse,
)
async def search_entities(
    schema_name: str,
    request: EntitySearchRequest,
    response: Response,
    tenant_id: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    store: DataServiceStore = Depends(get_store),
) -> EntitySearchResponse:
    """Search and filter entities with faceted results.

    Supports full-text search across payload fields, faceted filtering
    by specific field values, and configurable sort order.
    """
    all_records = await store.list_entities(schema_name, tenant_id, 0, 10000)

    query = request.query.strip().lower()
    filters = request.filters

    filtered: list[EntityRecord] = []
    for record in all_records:
        if query and not _entity_matches_query(record, query):
            continue
        if filters and not _entity_matches_filters(record, filters):
            continue
        filtered.append(record)

    sort_field = request.sort_by
    reverse = request.sort_order == "desc"
    filtered.sort(key=lambda r: _sort_key(r, sort_field), reverse=reverse)

    facet_fields = _discover_facet_fields(schema_name)
    facets = _compute_facets(filtered, facet_fields)

    total = len(filtered)
    page = filtered[skip: skip + limit]

    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(skip)

    return EntitySearchResponse(
        items=[_entity_response(r) for r in page],
        total=total,
        offset=skip,
        limit=limit,
        facets=facets,
    )


@api_router.get(
    "/entities/{schema_name}/facets",
    response_model=list[FacetResponse],
)
async def get_entity_facets(
    schema_name: str,
    tenant_id: str | None = Query(None),
    store: DataServiceStore = Depends(get_store),
) -> list[FacetResponse]:
    """Return facet value counts for a given entity collection."""
    all_records = await store.list_entities(schema_name, tenant_id, 0, 10000)
    facet_fields = _discover_facet_fields(schema_name)
    return _compute_facets(all_records, facet_fields)


@api_router.get("/scenarios", response_model=list[EntityResponse])
async def list_scenarios(
    response: Response,
    tenant_id: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    store: DataServiceStore = Depends(get_store),
) -> list[EntityResponse]:
    records = await store.list_entities(SCENARIO_SCHEMA, tenant_id, skip, limit)
    response.headers["X-Total-Count"] = str(await store.count_entities(SCENARIO_SCHEMA, tenant_id))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(skip)
    return [_entity_response(record) for record in records]


@api_router.get("/agent-runs", response_model=list[EntityResponse])
async def list_agent_runs(
    response: Response,
    tenant_id: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    store: DataServiceStore = Depends(get_store),
) -> list[EntityResponse]:
    _require_feature("agent_run_tracking")
    records = await store.list_entities(AGENT_RUN_SCHEMA, tenant_id, skip, limit)
    response.headers["X-Total-Count"] = str(await store.count_entities(AGENT_RUN_SCHEMA, tenant_id))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(skip)
    return [_entity_response(record) for record in records]


@api_router.post("/ingest/connector", response_model=ConnectorIngestResponse)
async def ingest_connector(
    request: ConnectorIngestRequest, store: DataServiceStore = Depends(get_store)
) -> ConnectorIngestResponse:
    module = _load_connector_module(request.connector_name)
    fixture_path = _resolve_fixture_path(request.connector_name, request.fixture_path)
    if request.live and fixture_path is None:
        fixture_path = None
    records = _invoke_connector(
        module,
        fixture_path,
        request.tenant_id,
        live=request.live,
    )
    grouped = _group_records_by_schema(records)
    schemas: dict[str, int] = {}
    canonical_mappings = None
    if _canonical_propagation_enabled():
        canonical_mappings = _load_canonical_mappings(request.connector_name)
    for schema_name, items in grouped.items():
        schema_record = await _resolve_schema(schema_name, None, store)
        await _require_schema_promotion_for_environment(schema_record, store)
        for item in items:
            payload = dict(item)
            payload["tenant_id"] = request.tenant_id
            _validate_payload(schema_record, payload)
            if canonical_mappings is not None:
                _validate_against_canonical_mapping(
                    schema_name, payload, request.connector_name, canonical_mappings
                )
            await store.store_entity(
                entity_id=payload.get("id") or str(uuid4()),
                tenant_id=request.tenant_id,
                schema_name=schema_name,
                schema_version=schema_record.version,
                payload=payload,
            )
        schemas[schema_name] = len(items)
    total = sum(schemas.values())
    return ConnectorIngestResponse(
        connector_name=request.connector_name,
        tenant_id=request.tenant_id,
        total_records=total,
        schemas=schemas,
        ingested_at=datetime.now(timezone.utc),
    )


def _schema_response(record: SchemaRecord) -> SchemaResponse:
    return SchemaResponse(
        name=record.name,
        version=record.version,
        schema=record.schema,
        created_at=record.created_at,
    )


def _entity_response(record: EntityRecord) -> EntityResponse:
    return EntityResponse(
        id=record.id,
        tenant_id=record.tenant_id,
        schema_name=record.schema_name,
        schema_version=record.schema_version,
        data=record.payload,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _validate_schema_definition(schema: dict[str, Any]) -> None:
    check_schema = getattr(Draft202012Validator, "check_schema", None)
    if check_schema is None:
        return
    try:
        check_schema(schema)
    except Exception as exc:  # pragma: no cover - upstream jsonschema exceptions vary
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _validate_payload(schema_record: SchemaRecord, payload: dict[str, Any]) -> None:
    validator = Draft202012Validator(schema_record.schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda err: err.path)
    if errors:
        formatted = "; ".join(error.message for error in errors)
        raise HTTPException(status_code=422, detail=f"Schema validation failed: {formatted}")


_CANONICAL_MAPPING_CACHE: dict[str, dict[str, set[str]]] = {}


def _load_canonical_mappings(connector_name: str) -> dict[str, set[str]]:
    if connector_name in _CANONICAL_MAPPING_CACHE:
        return _CANONICAL_MAPPING_CACHE[connector_name]
    connector_root = REPO_ROOT / "connectors" / connector_name
    manifest_path = connector_root / "manifest.yaml"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Connector manifest not found")
    manifest = load_yaml(manifest_path) or {}
    mappings = manifest.get("mappings", [])
    schema_targets: dict[str, set[str]] = {}
    for mapping in mappings:
        mapping_file = mapping.get("mapping_file")
        if not mapping_file:
            continue
        mapping_path = (connector_root / mapping_file).resolve()
        if not mapping_path.exists():
            raise HTTPException(status_code=422, detail=f"Mapping file not found: {mapping_file}")
        spec = load_yaml(mapping_path) or {}
        schema_name = spec.get("schema") or spec.get("target") or mapping.get("target")
        if not schema_name:
            continue
        fields = {
            entry.get("target") for entry in (spec.get("fields") or []) if entry.get("target")
        }
        schema_targets[schema_name] = fields
    _CANONICAL_MAPPING_CACHE[connector_name] = schema_targets
    return schema_targets


def _validate_against_canonical_mapping(
    schema_name: str,
    payload: dict[str, Any],
    connector_name: str,
    mapping_targets: dict[str, set[str]] | None = None,
) -> None:
    mapping_targets = mapping_targets or _load_canonical_mappings(connector_name)
    if schema_name not in mapping_targets:
        raise HTTPException(
            status_code=422,
            detail=f"No canonical mapping for schema '{schema_name}' in connector '{connector_name}'",
        )
    allowed = mapping_targets[schema_name] | {"tenant_id"}
    unexpected = set(payload.keys()) - allowed
    if unexpected:
        fields = ", ".join(sorted(unexpected))
        raise HTTPException(
            status_code=422,
            detail=(
                "Canonical mapping validation failed: "
                f"fields not mapped for {schema_name}: {fields}"
            ),
        )


async def _resolve_schema(
    schema_name: str, version: int | None, store: DataServiceStore
) -> SchemaRecord:
    if version is None:
        record = await store.get_latest_schema(schema_name)
    else:
        record = await store.get_schema(schema_name, version)
    if not record:
        raise HTTPException(status_code=404, detail="Schema not found")
    return record


def _load_connector_module(connector_name: str):
    try:
        return importlib.import_module(f"connectors.{connector_name}.src.main")
    except ModuleNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Connector not found") from exc


def _resolve_fixture_path(connector_name: str, fixture_path: str | None) -> Path | None:
    if fixture_path:
        path = Path(fixture_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Fixture file not found")
        return path
    default_fixture = (
        REPO_ROOT
        / "connectors"
        / connector_name
        / "tests"
        / "fixtures"
        / "projects.json"
    )
    if default_fixture.exists():
        return default_fixture
    return None


def _invoke_connector(
    module, fixture_path: Path | None, tenant_id: str, *, live: bool
) -> list[dict[str, Any]]:
    run_sync = getattr(module, "run_sync", None)
    if run_sync is None:
        raise HTTPException(status_code=400, detail="Connector missing run_sync entrypoint")
    parameters = inspect.signature(run_sync).parameters
    kwargs: dict[str, Any] = {}
    if "live" in parameters:
        kwargs["live"] = live
    if "include_schema" in parameters:
        kwargs["include_schema"] = True
    if fixture_path is None and "live" not in parameters:
        raise HTTPException(status_code=422, detail="Fixture path is required for this connector")
    return run_sync(fixture_path, tenant_id, **kwargs)


def _group_records_by_schema(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        schema_name = record.pop("schema_name", None)
        if not schema_name:
            continue
        grouped[schema_name].append(record)
    return grouped


def _paginate(items: list[Any], *, offset: int, limit: int) -> tuple[list[Any], int]:
    total = len(items)
    return items[offset : offset + limit], total


def _require_feature(flag_name: str) -> None:
    environment = os.getenv("ENVIRONMENT", "dev")
    if not is_feature_enabled(flag_name, environment=environment, default=False):
        raise HTTPException(status_code=403, detail=f"Feature flag '{flag_name}' is disabled")


def _canonical_propagation_enabled() -> bool:
    environment = os.getenv("ENVIRONMENT", "dev")
    return is_feature_enabled("canonical_propagation", environment=environment, default=False)


async def _require_schema_promotion_for_environment(
    schema_record: SchemaRecord, store: DataServiceStore
) -> None:
    environment = os.getenv("ENVIRONMENT", "dev").lower()
    if environment in {"dev", "local", "test"}:
        return
    promoted = await store.is_schema_promoted(
        schema_record.name,
        schema_record.version,
        environment,
    )
    if not promoted:
        raise HTTPException(
            status_code=409,
            detail=(
                "Schema version is not promoted for this environment: "
                f"{schema_record.name}@{schema_record.version} -> {environment}"
            ),
        )


def _entity_matches_query(record: EntityRecord, query: str) -> bool:
    """Check if any payload field contains the search query."""
    payload = record.payload or {}
    for value in payload.values():
        if isinstance(value, str) and query in value.lower():
            return True
        if isinstance(value, (int, float)) and query in str(value):
            return True
    if query in record.id.lower():
        return True
    return False


def _entity_matches_filters(record: EntityRecord, filters: dict[str, list[str]]) -> bool:
    """Check if entity payload matches all facet filters."""
    payload = record.payload or {}
    for field_name, accepted_values in filters.items():
        if not accepted_values:
            continue
        entity_value = str(payload.get(field_name, "")).lower()
        accepted_lower = [v.lower() for v in accepted_values]
        if entity_value not in accepted_lower:
            return False
    return True


def _sort_key(record: EntityRecord, field: str) -> Any:
    """Extract sort key from entity record."""
    if field == "updated_at":
        return record.updated_at
    if field == "created_at":
        return record.created_at
    if field == "id":
        return record.id
    payload = record.payload or {}
    value = payload.get(field, "")
    if isinstance(value, str):
        return value.lower()
    return str(value)


_FACET_FIELD_CACHE: dict[str, list[str]] = {}

_SCHEMA_FACET_FIELDS: dict[str, list[str]] = {
    "project": ["status", "owner", "regulatory_category", "classification"],
    "portfolio": ["status", "owner", "classification"],
    "program": ["status", "owner", "classification"],
    "risk": ["status", "impact", "likelihood", "owner", "classification"],
    "issue": ["status", "priority", "owner", "classification"],
    "work-item": ["status", "type", "assigned_to", "classification"],
    "document": ["status", "type", "classification"],
    "budget": ["status", "classification"],
    "resource": ["status", "role", "classification"],
    "vendor": ["status", "classification"],
    "demand": ["status", "priority", "classification"],
}


def _discover_facet_fields(schema_name: str) -> list[str]:
    """Discover which fields are suitable for faceting."""
    if schema_name in _FACET_FIELD_CACHE:
        return _FACET_FIELD_CACHE[schema_name]

    fields = list(_SCHEMA_FACET_FIELDS.get(schema_name, ["status", "owner", "classification"]))

    schema_path = SCHEMA_DIR / f"{schema_name}.schema.json"
    if schema_path.exists():
        import json

        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            properties = schema.get("properties", {})
            for prop_name, prop_def in properties.items():
                if "enum" in prop_def and prop_name not in fields:
                    fields.append(prop_name)
        except (json.JSONDecodeError, OSError):
            pass

    _FACET_FIELD_CACHE[schema_name] = fields
    return fields


def _compute_facets(
    records: list[EntityRecord], facet_fields: list[str]
) -> list[FacetResponse]:
    """Compute facet value counts from a list of entity records."""
    counters: dict[str, dict[str, int]] = {field: {} for field in facet_fields}

    for record in records:
        payload = record.payload or {}
        for field in facet_fields:
            value = payload.get(field)
            if value is not None:
                str_value = str(value)
                counters[field][str_value] = counters[field].get(str_value, 0) + 1

    facets: list[FacetResponse] = []
    for field in facet_fields:
        buckets = sorted(
            [FacetBucket(value=v, count=c) for v, c in counters[field].items()],
            key=lambda b: (-b.count, b.value),
        )
        if buckets:
            facets.append(FacetResponse(field=field, buckets=buckets))

    return facets


app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
