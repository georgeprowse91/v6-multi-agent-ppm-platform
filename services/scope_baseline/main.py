"""
Scope Baseline Service – FastAPI entry point.

Provides REST endpoints for creating, retrieving, and listing
project scope baseline snapshots.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from packages.version import API_VERSION
except ImportError:
    API_VERSION = "1.0.0"

from .scope_baseline_service import create_baseline, list_baselines, retrieve_baseline  # noqa: E402

logger = logging.getLogger("scope-baseline")
logging.basicConfig(level=logging.INFO)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "scope-baseline"
    version: str = API_VERSION


class CreateBaselineRequest(BaseModel):
    baseline_id: str | None = Field(None, description="Optional stable identifier for idempotency")
    version: str = Field("1.0", description="Baseline version label")
    created_by: str = Field(..., description="User or system that created this baseline")
    data: dict[str, Any] = Field(..., description="Scope snapshot payload")


class BaselineResponse(BaseModel):
    baseline_id: str
    project_id: str
    version: str
    created_by: str
    timestamp: str
    data: dict[str, Any]


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    app = FastAPI(
        title="Scope Baseline Service",
        description="Store and retrieve immutable project scope baseline snapshots.",
        version=API_VERSION,
    )

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        return HealthResponse()

    @app.post(
        "/projects/{project_id}/baselines",
        response_model=BaselineResponse,
        status_code=201,
        tags=["baselines"],
    )
    def create_project_baseline(project_id: str, body: CreateBaselineRequest) -> BaselineResponse:
        """Capture a new scope baseline for a project."""
        payload: dict[str, Any] = {
            "version": body.version,
            "created_by": body.created_by,
            **body.data,
        }
        if body.baseline_id:
            payload["baseline_id"] = body.baseline_id
        baseline_id = create_baseline(project_id, payload)
        record = retrieve_baseline(baseline_id)
        return BaselineResponse(**record)

    @app.get(
        "/projects/{project_id}/baselines",
        response_model=list[BaselineResponse],
        tags=["baselines"],
    )
    def list_project_baselines(project_id: str) -> list[BaselineResponse]:
        """List all baselines for a project, newest first."""
        records = list_baselines(project_id)
        return [BaselineResponse(**r) for r in records]

    @app.get(
        "/baselines/{baseline_id}",
        response_model=BaselineResponse,
        tags=["baselines"],
    )
    def get_baseline(baseline_id: str) -> BaselineResponse:
        """Retrieve a single baseline by ID."""
        try:
            record = retrieve_baseline(baseline_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return BaselineResponse(**record)

    return app


app = create_app()
