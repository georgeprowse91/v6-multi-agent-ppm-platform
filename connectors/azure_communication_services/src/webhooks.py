from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle ACS event grid payloads."""
    return {
        "connector_id": "azure_communication_services",
        "event_type": headers.get("aeg-event-type", "notification"),
        "resource_id": payload.get("messageId"),
    }


def register_webhook(webhook_url: str, secret: str, config: Any | None = None) -> dict[str, Any]:
    """Register webhook delivery endpoint."""
    return {
        "connector_id": "azure_communication_services",
        "status": "registered",
        "webhook_url": webhook_url,
    }
