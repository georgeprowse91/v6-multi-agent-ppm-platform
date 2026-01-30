from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle SharePoint webhook notifications."""
    value = payload.get("value", [])
    return {
        "connector_id": "sharepoint",
        "event_type": "notification",
        "subscription_id": value[0].get("subscriptionId") if value else None,
        "resource": value[0].get("resource") if value else None,
    }


def register_webhook(webhook_url: str, secret: str, config: Any | None = None) -> dict[str, Any]:
    """Register webhook delivery endpoint."""
    return {
        "connector_id": "sharepoint",
        "status": "registered",
        "webhook_url": webhook_url,
    }
