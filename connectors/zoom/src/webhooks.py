from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle Zoom webhook events."""
    return {
        "connector_id": "zoom",
        "event_type": payload.get("event"),
        "resource": payload.get("payload", {}).get("object", {}).get("id"),
    }
