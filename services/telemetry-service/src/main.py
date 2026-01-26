from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from otel import PIPELINE
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
if str(SECURITY_ROOT) not in sys.path:
    sys.path.insert(0, str(SECURITY_ROOT))

from security.auth import AuthTenantMiddleware  # noqa: E402

logger = logging.getLogger("telemetry-service")
logging.basicConfig(level=logging.INFO)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "telemetry-service"


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


app = FastAPI(title="Telemetry Service", version="0.1.0")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz"})


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()


@app.post("/telemetry/ingest", response_model=TelemetryResponse)
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
    return TelemetryResponse(
        ingested=True,
        correlation_id=correlation_id,
        stored_at=datetime.now(timezone.utc),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
