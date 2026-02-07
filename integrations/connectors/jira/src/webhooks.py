from __future__ import annotations

from typing import Any


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """Handle Jira webhook events."""
    issue = payload.get("issue", {})
    return {
        "connector_id": "jira",
        "event_type": payload.get("webhookEvent", "unknown"),
        "issue_key": issue.get("key"),
    }


def register_webhook(webhook_url: str, secret: str, config: Any | None = None) -> dict[str, Any]:
    """Register webhook delivery endpoint."""
    return {
        "connector_id": "jira",
        "status": "registered",
        "webhook_url": webhook_url,
    }
