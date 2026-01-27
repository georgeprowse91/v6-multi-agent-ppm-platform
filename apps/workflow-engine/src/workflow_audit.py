from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx

logger = logging.getLogger("workflow-engine-audit")


def emit_audit_event(
    tenant_id: str,
    actor: dict[str, Any],
    action: str,
    resource: dict[str, Any],
    classification: str,
) -> None:
    audit_url = os.getenv("AUDIT_LOG_URL")
    if not audit_url:
        return
    token = os.getenv("AUDIT_LOG_SERVICE_TOKEN")
    if not token:
        logger.warning("audit_log_token_missing")
        return
    payload = {
        "id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "action": action,
        "outcome": "success",
        "classification": classification,
        "actor": actor,
        "resource": resource,
    }
    try:
        httpx.post(
            f"{audit_url}/audit/events",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
            timeout=5.0,
        )
    except httpx.HTTPError:
        return
