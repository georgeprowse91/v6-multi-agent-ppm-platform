from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle Teams webhook notifications."""
    return {
        "connector_id": "teams",
        "event_type": payload.get("value", [{}])[0].get("changeType", "unknown"),
        "resource": payload.get("value", [{}])[0].get("resource"),
    }


def register_webhook(webhook_url: str, secret: str, config: Any | None = None) -> dict[str, Any]:
    """Register webhook delivery endpoint."""
    return {
        "connector_id": "teams",
        "status": "registered",
        "webhook_url": webhook_url,
    }
