from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, FastAPI
from otel import PIPELINE
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
_common_src = REPO_ROOT / "packages" / "common" / "src"
if str(_common_src) not in sys.path:
    sys.path.insert(0, str(_common_src))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402
ensure_monorepo_paths(REPO_ROOT)

from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from security.api_governance import (  # noqa: E402
    apply_api_governance,
    version_response_payload,
)
from security.auth import AuthTenantMiddleware  # noqa: E402

from packages.version import API_VERSION  # noqa: E402

logger = logging.getLogger("telemetry-service")
logging.basicConfig(level=logging.INFO)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "telemetry-service"
    dependencies: dict[str, str] = Field(default_factory=dict)


class TelemetryEnvelope(BaseModel):
    source: str
    type: str = Field("log", description="log|metric|trace")
    timestamp: datetime | None = None
    correlation_id: str | None = None
    payload: dict[str, Any]


class TelemetryResponse(BaseModel):
    ingested: bool
    correlation_id: str
    stored_at: datetime


app = FastAPI(title="Telemetry Service", version=API_VERSION, openapi_prefix="/v1")
api_router = APIRouter(prefix="/v1")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz", "/version"})
configure_tracing("telemetry-service")
configure_metrics("telemetry-service")
app.add_middleware(TraceMiddleware, service_name="telemetry-service")
app.add_middleware(RequestMetricsMiddleware, service_name="telemetry-service")
apply_api_governance(app, service_name="telemetry-service")

telemetry_ingest_total = configure_metrics("telemetry-service").create_counter(
    name="telemetry_ingest_total",
    description="Telemetry envelopes ingested",
    unit="1",
)


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    dependencies = {"otel_pipeline": "ok" if PIPELINE else "down"}
    status = "ok" if all(value == "ok" for value in dependencies.values()) else "degraded"
    return HealthResponse(status=status, dependencies=dependencies)


@app.get("/version")
async def version() -> dict[str, str]:
    return version_response_payload("telemetry-service")


@api_router.post("/telemetry/ingest", response_model=TelemetryResponse)
async def ingest(payload: TelemetryEnvelope) -> TelemetryResponse:
    correlation_id = payload.correlation_id or str(uuid4())
    timestamp = payload.timestamp or datetime.now(timezone.utc)
    tracer = PIPELINE.tracer()
    with tracer.start_as_current_span("telemetry.ingest") as span:
        span.set_attribute("telemetry.source", payload.source)
        span.set_attribute("telemetry.type", payload.type)
        span.set_attribute("telemetry.correlation_id", correlation_id)
        span.set_attribute("telemetry.timestamp", timestamp.isoformat())
        span.set_attribute("telemetry.payload", str(payload.payload))

    logger.info(
        "telemetry_ingested",
        extra={"correlation_id": correlation_id, "type": payload.type},
    )
    telemetry_ingest_total.add(1, {"type": payload.type})
    return TelemetryResponse(
        ingested=True,
        correlation_id=correlation_id,
        stored_at=datetime.now(timezone.utc),
    )


app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
