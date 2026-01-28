from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query
from jsonschema import Draft202012Validator, FormatChecker, SchemaError
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for root in (SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
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


def get_store() -> DataServiceStore:
    return app.state.store


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
