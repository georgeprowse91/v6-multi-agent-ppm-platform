from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle Slack events API payloads."""
    event = payload.get("event", {})
    return {
        "connector_id": "slack",
        "event_type": event.get("type", payload.get("type", "unknown")),
        "channel": event.get("channel"),
        "user": event.get("user"),
    }


def register_webhook(webhook_url: str, secret: str, config: Any | None = None) -> dict[str, Any]:
    """Register webhook delivery endpoint."""
    return {
        "connector_id": "slack",
        "status": "registered",
        "webhook_url": webhook_url,
    }
