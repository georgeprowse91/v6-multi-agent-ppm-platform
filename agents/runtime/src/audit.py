from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib import request

logger = logging.getLogger("agents.runtime.audit")


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
    logger.info("audit_event", extra=event)
    endpoint = os.getenv("AUDIT_LOG_ENDPOINT")
    if not endpoint:
        return
    payload = json.dumps(event).encode("utf-8")
    req = request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=5) as response:
        response.read()
