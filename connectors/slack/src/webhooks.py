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
