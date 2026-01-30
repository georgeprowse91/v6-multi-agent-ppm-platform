from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle ServiceNow webhook events."""
    return {
        "connector_id": "servicenow_grc",
        "event_type": payload.get("event", "unknown"),
        "record_id": payload.get("sys_id"),
    }
