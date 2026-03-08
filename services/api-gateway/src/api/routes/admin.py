"""
Admin API Routes

Operational endpoints for zero-downtime cache management and credential rotation.
All routes under /v1/admin require ``config.write`` permission (enforced by the
RBAC middleware in ``api.middleware.security``).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

router = APIRouter()
logger = logging.getLogger("api-gateway-admin")


def _actor(request: Request) -> str:
    auth = getattr(request.state, "auth", None)
    return getattr(auth, "subject", "unknown") if auth else "unknown"


@router.post(
    "/model-registry/cache/clear",
    summary="Clear model registry LRU cache",
    response_model=dict,
)
async def clear_model_registry_cache_endpoint(request: Request) -> dict[str, Any]:
    """Invalidate the in-process model registry cache.

    After this call the next invocation of ``load_model_registry()`` will
    re-read ``apps/web/data/llm_models.json`` from disk, enabling zero-downtime
    registry updates without a process restart.

    Requires ``config.write`` permission (enforced by RBAC middleware).
    """
    from model_registry import clear_model_registry_cache

    clear_model_registry_cache()
    logger.info("model_registry_cache_cleared", extra={"actor": _actor(request)})
    return {"status": "ok", "message": "Model registry cache cleared"}


@router.post(
    "/llm/keys/rotate",
    summary="Trigger in-process LLM credential rotation",
    response_model=dict,
)
async def rotate_llm_keys_endpoint(request: Request) -> dict[str, Any]:
    """Trigger in-process LLM API key and JWKS cache rotation.

    Clears the OIDC discovery document cache and the JWKS cache maintained by
    ``security.auth``, forcing fresh resolution on the next inbound request.
    This is the HTTP-triggered complement to the SIGUSR1 signal handler
    installed at startup.

    Requires ``config.write`` permission (enforced by RBAC middleware).
    """
    from security.auth import clear_auth_caches

    clear_auth_caches()
    logger.info("llm_key_rotation_endpoint_triggered", extra={"actor": _actor(request)})
    return {
        "status": "ok",
        "message": "Auth caches cleared; fresh resolution on next request",
    }
