from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle Monday.com webhook payloads."""
    return {
        "connector_id": "monday",
        "event_type": payload.get("event", {}).get("type", "unknown"),
        "board_id": payload.get("event", {}).get("boardId"),
        "item_id": payload.get("event", {}).get("pulseId"),
    }
