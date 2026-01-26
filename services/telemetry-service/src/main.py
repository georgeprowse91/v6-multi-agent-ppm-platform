from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field

logger = logging.getLogger("telemetry-service")
logging.basicConfig(level=logging.INFO)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORAGE_PATH = REPO_ROOT / "services" / "telemetry-service" / "pipelines" / "telemetry.jsonl"


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


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()


def _ensure_storage(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()


@app.post("/telemetry/ingest", response_model=TelemetryResponse)
async def ingest(payload: TelemetryEnvelope) -> TelemetryResponse:
    correlation_id = payload.correlation_id or str(uuid4())
    timestamp = payload.timestamp or datetime.now(timezone.utc)
    record = {
        "source": payload.source,
        "type": payload.type,
        "timestamp": timestamp.isoformat(),
        "correlation_id": correlation_id,
        "payload": payload.payload,
    }

    storage_path = Path(os.getenv("TELEMETRY_STORAGE_PATH", str(DEFAULT_STORAGE_PATH)))
    _ensure_storage(storage_path)
    with storage_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")

    logger.info("telemetry_ingested", extra={"correlation_id": correlation_id, "type": payload.type})
    return TelemetryResponse(
        ingested=True,
        correlation_id=correlation_id,
        stored_at=datetime.now(timezone.utc),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
