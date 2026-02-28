from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle Google Calendar push notifications."""
    return {
        "connector_id": "google_calendar",
        "event_type": headers.get("x-goog-event", "notification"),
        "resource_id": headers.get("x-goog-resource-id"),
    }


def register_webhook(webhook_url: str, secret: str, config: Any | None = None) -> dict[str, Any]:
    """Register webhook delivery endpoint."""
    return {
        "connector_id": "google_calendar",
        "status": "registered",
        "webhook_url": webhook_url,
    }
