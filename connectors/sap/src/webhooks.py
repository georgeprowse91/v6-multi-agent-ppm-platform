from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle SAP webhook events."""
    event_type = headers.get("x-sap-event", payload.get("event_type", "unknown"))
    return {
        "connector_id": "sap",
        "event_type": event_type,
        "resource": payload.get("resource"),
    }


def register_webhook(webhook_url: str, secret: str, config: Any | None = None) -> dict[str, Any]:
    """Register webhook delivery endpoint."""
    return {
        "connector_id": "sap",
        "status": "registered",
        "webhook_url": webhook_url,
    }
