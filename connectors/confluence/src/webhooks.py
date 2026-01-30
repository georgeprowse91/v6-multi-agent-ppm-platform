from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle Confluence webhook events."""
    return {
        "connector_id": "confluence",
        "event_type": payload.get("event", "unknown"),
        "content_id": payload.get("content", {}).get("id"),
    }


def register_webhook(webhook_url: str, secret: str, config: Any | None = None) -> dict[str, Any]:
    """Register webhook delivery endpoint."""
    return {
        "connector_id": "confluence",
        "status": "registered",
        "webhook_url": webhook_url,
    }
