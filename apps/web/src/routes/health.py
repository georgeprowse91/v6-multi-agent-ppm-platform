"""Health and version endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Response

from routes._deps import (
    WORKFLOW_DEFINITIONS_PATH,
    knowledge_store,
    intake_store,
    pipeline_store,
    version_response_payload,
)
from routes._models import HealthResponse

router = APIRouter()


@router.get("/healthz", response_model=HealthResponse)
async def healthz(response: Response) -> HealthResponse:
    dependencies = {
        "knowledge_store": "ok" if knowledge_store else "down",
        "intake_store": "ok" if intake_store else "down",
        "pipeline_store": "ok" if pipeline_store else "down",
        "workflow_definitions": "ok" if WORKFLOW_DEFINITIONS_PATH.exists() else "down",
    }
    status = "ok" if all(value == "ok" for value in dependencies.values()) else "degraded"
    if status != "ok":
        response.status_code = 503
    return HealthResponse(status=status, dependencies=dependencies)


@router.get("/version")
async def version() -> dict[str, str]:
    return version_response_payload("web")
