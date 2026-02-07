from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle LogicGate webhook payloads."""
    return {
        "connector_id": "logicgate",
        "event_type": payload.get("event", "unknown"),
        "record_id": payload.get("record", {}).get("id"),
    }


def register_webhook(webhook_url: str, secret: str, config: Any | None = None) -> dict[str, Any]:
    """Register webhook delivery endpoint."""
    return {
        "connector_id": "logicgate",
        "status": "registered",
        "webhook_url": webhook_url,
    }
