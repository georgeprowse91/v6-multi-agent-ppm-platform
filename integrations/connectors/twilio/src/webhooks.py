from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle Twilio webhook payloads."""
    return {
        "connector_id": "twilio",
        "event_type": headers.get("X-Twilio-Event", "message"),
        "resource_id": payload.get("MessageSid"),
    }


def register_webhook(webhook_url: str, secret: str, config: Any | None = None) -> dict[str, Any]:
    """Register webhook delivery endpoint."""
    return {
        "connector_id": "twilio",
        "status": "registered",
        "webhook_url": webhook_url,
    }
