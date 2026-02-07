from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle Notification Hubs payloads."""
    return {
        "connector_id": "notification_hubs",
        "event_type": headers.get("x-event-type", "notification"),
        "resource_id": payload.get("notificationId"),
    }


def register_webhook(webhook_url: str, secret: str, config: Any | None = None) -> dict[str, Any]:
    """Register webhook delivery endpoint."""
    return {
        "connector_id": "notification_hubs",
        "status": "registered",
        "webhook_url": webhook_url,
    }
