from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger("agents.runtime.audit")

_AUDIT_HTTP_CLIENT: httpx.AsyncClient | None = None
_AUDIT_EMIT_TIMEOUT: float = 5.0


def _get_audit_client() -> httpx.AsyncClient:
    global _AUDIT_HTTP_CLIENT
    if _AUDIT_HTTP_CLIENT is None or _AUDIT_HTTP_CLIENT.is_closed:
        _AUDIT_HTTP_CLIENT = httpx.AsyncClient(timeout=_AUDIT_EMIT_TIMEOUT)
    return _AUDIT_HTTP_CLIENT


def build_audit_event(
    *,
    tenant_id: str,
    action: str,
    outcome: str,
    actor_id: str,
    actor_type: str,
    actor_roles: list[str] | None,
    resource_id: str,
    resource_type: str,
    metadata: dict[str, Any] | None = None,
    classification: str = "internal",
    trace_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": f"evt-{uuid.uuid4().hex}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "action": action,
        "outcome": outcome,
        "classification": classification,
        "actor": {
            "id": actor_id,
            "type": actor_type,
            "roles": actor_roles or [],
        },
        "resource": {
            "id": resource_id,
            "type": resource_type,
            "attributes": metadata or {},
        },
        "metadata": metadata or {},
        "trace_id": trace_id,
        "correlation_id": correlation_id,
    }


def emit_audit_event(event: dict[str, Any]) -> None:
    """Emit an audit event: log it and, if configured, send to the audit endpoint.

    The HTTP POST is performed asynchronously via a background task when an
    event loop is running.  Falls back to a synchronous fire-and-forget call
    when no loop is available (e.g. during tests or CLI scripts).
    """
    logger.info("audit_event", extra=event)
    endpoint = os.getenv("AUDIT_LOG_ENDPOINT")
    if not endpoint:
        return

    async def _send() -> None:
        try:
            client = _get_audit_client()
            response = await client.post(
                endpoint,
                json=event,
                headers={"Content-Type": "application/json"},
            )
            if response.status_code >= 400:
                logger.warning(
                    "audit_emit_failed",
                    extra={"status": response.status_code, "endpoint": endpoint},
                )
        except (httpx.HTTPError, OSError) as exc:
            logger.warning("audit_emit_error", extra={"error": str(exc), "endpoint": endpoint})

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_send())
    except RuntimeError:
        # No running event loop – fall back to synchronous call.
        try:
            with httpx.Client(timeout=_AUDIT_EMIT_TIMEOUT) as sync_client:
                sync_client.post(
                    endpoint,
                    json=event,
                    headers={"Content-Type": "application/json"},
                )
        except (httpx.HTTPError, OSError) as exc:
            logger.warning("audit_emit_error", extra={"error": str(exc), "endpoint": endpoint})
