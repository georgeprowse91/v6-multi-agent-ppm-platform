from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle Outlook/Graph webhook payloads."""
    value = payload.get("value", [{}])
    event = value[0] if isinstance(value, list) and value else {}
    return {
        "connector_id": "outlook",
        "event_type": headers.get("x-event-type", "notification"),
        "resource_id": event.get("resourceData", {}).get("id"),
    }


def register_webhook(webhook_url: str, secret: str, config: Any | None = None) -> dict[str, Any]:
    """Register webhook delivery endpoint."""
    return {
        "connector_id": "outlook",
        "status": "registered",
        "webhook_url": webhook_url,
    }
