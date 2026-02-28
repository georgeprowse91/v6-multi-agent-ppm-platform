from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle Smartsheet webhook payloads."""
    return {
        "connector_id": "smartsheet",
        "event_type": payload.get("eventType", headers.get("x-event-type", "unknown")),
        "resource_id": payload.get("scopeObjectId"),
    }


def register_webhook(webhook_url: str, secret: str, config: Any | None = None) -> dict[str, Any]:
    """Register webhook delivery endpoint."""
    return {
        "connector_id": "smartsheet",
        "status": "registered",
        "webhook_url": webhook_url,
    }
