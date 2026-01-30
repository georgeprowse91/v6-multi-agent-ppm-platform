from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle Azure DevOps webhook payloads."""
    event_type = headers.get("x-vss-event", payload.get("eventType", "unknown"))
    return {
        "connector_id": "azure_devops",
        "event_type": event_type,
        "resource": payload.get("resource"),
    }
