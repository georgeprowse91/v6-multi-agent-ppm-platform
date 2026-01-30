from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle Zoom webhook events."""
    return {
        "connector_id": "zoom",
        "event_type": payload.get("event"),
        "resource": payload.get("payload", {}).get("object", {}).get("id"),
    }


def register_webhook(webhook_url: str, secret: str, config: Any | None = None) -> dict[str, Any]:
    """Register webhook delivery endpoint."""
    return {
        "connector_id": "zoom",
        "status": "registered",
        "webhook_url": webhook_url,
    }
