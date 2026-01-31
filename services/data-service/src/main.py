from __future__ import annotations

import importlib
import inspect
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from jsonschema import Draft202012Validator, FormatChecker, SchemaError

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for root in (REPO_ROOT, SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from retention_scheduler import RetentionScheduler  # noqa: E402
from security.auth import AuthTenantMiddleware  # noqa: E402
from storage import (  # noqa: E402
    DataServiceStore,
    EntityRecord,
    SchemaExistsError,
    SchemaRecord,
    to_async_database_url,
)

logger = logging.getLogger("data-service")
logging.basicConfig(level=logging.INFO)

SCHEMA_DIR = REPO_ROOT / "data" / "schemas"


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "data-service"


class SchemaRegistrationRequest(BaseModel):
    name: str = Field(..., description="Canonical schema name")
    schema: dict[str, Any] = Field(..., description="JSON Schema payload")
    version: int | None = Field(None, description="Optional schema version override")


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


class EntityResponse(BaseModel):
    id: str
    tenant_id: str
    schema_name: str
    schema_version: int
    data: dict[str, Any]
    created_at: datetime
    updated_at: datetime


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


app = FastAPI(title="Data Service", version="0.1.0")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz"})
configure_tracing("data-service")
configure_metrics("data-service")
app.add_middleware(TraceMiddleware, service_name="data-service")
app.add_middleware(RequestMetricsMiddleware, service_name="data-service")


@app.on_event("startup")
async def startup() -> None:
    database_url = os.getenv("DATA_SERVICE_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        database_url = "sqlite+aiosqlite:///data/data_service.db"
    database_url = to_async_database_url(database_url)
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


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()


@app.get("/retention/status", response_model=RetentionStatusResponse)
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


@app.post("/schemas", response_model=SchemaResponse)
async def register_schema(
    request: SchemaRegistrationRequest, store: DataServiceStore = Depends(get_store)
) -> SchemaResponse:
    try:
        Draft202012Validator.check_schema(request.schema)
    except SchemaError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        record = await store.register_schema(request.name, request.schema, request.version)
    except SchemaExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return _schema_response(record)


@app.get("/schemas", response_model=list[SchemaSummaryResponse])
async def list_schemas(store: DataServiceStore = Depends(get_store)) -> list[SchemaSummaryResponse]:
    summaries = await store.list_schema_summaries()
    return [SchemaSummaryResponse(**summary.__dict__) for summary in summaries]


@app.get("/schemas/{schema_name}/versions", response_model=list[SchemaResponse])
async def list_schema_versions(
    schema_name: str, store: DataServiceStore = Depends(get_store)
) -> list[SchemaResponse]:
    records = await store.list_schema_versions(schema_name)
    return [_schema_response(record) for record in records]


@app.get("/schemas/{schema_name}/latest", response_model=SchemaResponse)
async def get_latest_schema(
    schema_name: str, store: DataServiceStore = Depends(get_store)
) -> SchemaResponse:
    record = await store.get_latest_schema(schema_name)
    if not record:
        raise HTTPException(status_code=404, detail="Schema not found")
    return _schema_response(record)


@app.get("/schemas/{schema_name}/versions/{version}", response_model=SchemaResponse)
async def get_schema_version(
    schema_name: str, version: int, store: DataServiceStore = Depends(get_store)
) -> SchemaResponse:
    record = await store.get_schema(schema_name, version)
    if not record:
        raise HTTPException(status_code=404, detail="Schema not found")
    return _schema_response(record)


@app.get("/schemas/{schema_name}/promotions", response_model=list[SchemaPromotionResponse])
async def list_schema_promotions(
    schema_name: str, store: DataServiceStore = Depends(get_store)
) -> list[SchemaPromotionResponse]:
    promotions = await store.list_schema_promotions(schema_name)
    return [SchemaPromotionResponse(**promo.__dict__) for promo in promotions]


@app.post(
    "/schemas/{schema_name}/versions/{version}/promote",
    response_model=SchemaPromotionResponse,
)
async def promote_schema_version(
    schema_name: str,
    version: int,
    request: SchemaPromotionRequest,
    store: DataServiceStore = Depends(get_store),
) -> SchemaPromotionResponse:
    record = await store.get_schema(schema_name, version)
    if not record:
        raise HTTPException(status_code=404, detail="Schema version not found")
    promotion = await store.promote_schema(schema_name, version, request.environment)
    return SchemaPromotionResponse(**promotion.__dict__)


@app.post("/entities/{schema_name}", response_model=EntityResponse)
async def ingest_entity(
    schema_name: str,
    request: EntityIngestRequest,
    store: DataServiceStore = Depends(get_store),
) -> EntityResponse:
    record = await _resolve_schema(schema_name, request.schema_version, store)
    _validate_payload(record, request.data)
    entity_id = request.entity_id or request.data.get("id") or str(uuid4())
    stored = await store.store_entity(
        entity_id=entity_id,
        tenant_id=request.tenant_id,
        schema_name=schema_name,
        schema_version=record.version,
        payload=request.data,
    )
    return _entity_response(stored)


@app.get("/entities/{schema_name}/{entity_id}", response_model=EntityResponse)
async def get_entity(
    schema_name: str, entity_id: str, store: DataServiceStore = Depends(get_store)
) -> EntityResponse:
    record = await store.get_entity(schema_name, entity_id)
    if not record:
        raise HTTPException(status_code=404, detail="Entity not found")
    return _entity_response(record)


@app.get("/entities/{schema_name}", response_model=list[EntityResponse])
async def list_entities(
    schema_name: str,
    tenant_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    store: DataServiceStore = Depends(get_store),
) -> list[EntityResponse]:
    records = await store.list_entities(schema_name, tenant_id, limit)
    return [_entity_response(record) for record in records]


@app.post("/ingest/connector", response_model=ConnectorIngestResponse)
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
    for schema_name, items in grouped.items():
        schema_record = await _resolve_schema(schema_name, None, store)
        for item in items:
            payload = dict(item)
            payload["tenant_id"] = request.tenant_id
            _validate_payload(schema_record, payload)
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


def _validate_payload(schema_record: SchemaRecord, payload: dict[str, Any]) -> None:
    validator = Draft202012Validator(schema_record.schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda err: err.path)
    if errors:
        formatted = "; ".join(error.message for error in errors)
        raise HTTPException(status_code=422, detail=f"Schema validation failed: {formatted}")


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
        REPO_ROOT / "connectors" / connector_name / "tests" / "fixtures" / "projects.json"
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
