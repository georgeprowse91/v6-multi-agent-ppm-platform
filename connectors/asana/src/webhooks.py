from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle Asana webhook payloads."""
    event = payload.get("events", [{}])[0]
    return {
        "connector_id": "asana",
        "event_type": event.get("action", "unknown"),
        "resource_gid": event.get("resource", {}).get("gid"),
    }
