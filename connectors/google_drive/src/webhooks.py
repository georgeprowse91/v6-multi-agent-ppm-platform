from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle Google Drive webhook notifications."""
    return {
        "connector_id": "google_drive",
        "event_type": headers.get("x-goog-resource-state", "unknown"),
        "resource_id": headers.get("x-goog-resource-id"),
    }
