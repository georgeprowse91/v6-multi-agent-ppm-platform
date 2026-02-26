"""
Memory Service – FastAPI entry point.

Exposes a REST API for storing and retrieving conversation context,
backed by an in-memory or SQLite store with optional TTL support.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[2]
_COMMON_SRC = REPO_ROOT / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(REPO_ROOT)

try:
    from packages.version import API_VERSION
except ImportError:
    API_VERSION = "1.0.0"

from .memory_service import MemoryService  # noqa: E402

logger = logging.getLogger("memory-service")
logging.basicConfig(level=logging.INFO)

_BACKEND = os.getenv("MEMORY_SERVICE_BACKEND", "memory")
_SQLITE_PATH = os.getenv("MEMORY_SERVICE_SQLITE_PATH")
_DEFAULT_TTL = int(os.getenv("MEMORY_SERVICE_DEFAULT_TTL_SECONDS", "0")) or None

_service: MemoryService | None = None


def _get_service() -> MemoryService:
    global _service
    if _service is None:
        _service = MemoryService(
            backend=_BACKEND,
            sqlite_path=_SQLITE_PATH,
            default_ttl_seconds=_DEFAULT_TTL,
        )
    return _service


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "memory-service"
    backend: str = _BACKEND
    version: str = API_VERSION


class SaveContextRequest(BaseModel):
    data: dict[str, Any] = Field(..., description="Arbitrary key/value context to persist")


class ContextResponse(BaseModel):
    key: str
    data: dict[str, Any]


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    app = FastAPI(
        title="Memory Service",
        description="Conversation-context key-value store with optional TTL and SQLite persistence.",
        version=API_VERSION,
    )

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        return HealthResponse()

    @app.put("/contexts/{key}", response_model=ContextResponse, tags=["contexts"])
    def save_context(key: str, body: SaveContextRequest) -> ContextResponse:
        """Persist a context dict under the given key."""
        _get_service().save_context(key, body.data)
        return ContextResponse(key=key, data=body.data)

    @app.get("/contexts/{key}", response_model=ContextResponse, tags=["contexts"])
    def load_context(key: str) -> ContextResponse:
        """Retrieve a previously saved context by key."""
        data = _get_service().load_context(key)
        if data is None:
            raise HTTPException(status_code=404, detail=f"Context not found or expired: {key}")
        return ContextResponse(key=key, data=data)

    @app.delete("/contexts/{key}", tags=["contexts"])
    def delete_context(key: str) -> dict[str, str]:
        """Delete a stored context."""
        _get_service().delete_context(key)
        return {"status": "deleted", "key": key}

    @app.on_event("shutdown")
    def shutdown() -> None:
        if _service is not None:
            _service.close()

    return app


app = create_app()
