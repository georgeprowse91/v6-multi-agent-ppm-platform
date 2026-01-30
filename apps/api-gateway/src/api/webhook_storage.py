from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class WebhookEvent:
    event_id: str
    connector_id: str
    received_at: datetime
    payload: dict[str, Any]
    headers: dict[str, str]
    result: dict[str, Any] | None = None
    tenant_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "connector_id": self.connector_id,
            "received_at": self.received_at.isoformat(),
            "payload": self.payload,
            "headers": self.headers,
            "result": self.result,
            "tenant_id": self.tenant_id,
        }

    @classmethod
    def from_payload(
        cls,
        connector_id: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        result: dict[str, Any] | None = None,
        tenant_id: str | None = None,
    ) -> "WebhookEvent":
        return cls(
            event_id=str(uuid4()),
            connector_id=connector_id,
            received_at=datetime.now(timezone.utc),
            payload=payload,
            headers=headers,
            result=result,
            tenant_id=tenant_id,
        )


class WebhookEventStore:
    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_path = storage_path or Path(
            os.getenv("WEBHOOK_EVENTS_PATH", "data/connectors/webhooks.json")
        )
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_all(self) -> list[dict[str, Any]]:
        if not self.storage_path.exists():
            return []
        return json.loads(self.storage_path.read_text())

    def _save_all(self, events: list[dict[str, Any]]) -> None:
        self.storage_path.write_text(json.dumps(events, indent=2))

    def record_event(self, event: WebhookEvent) -> None:
        events = self._load_all()
        events.append(event.to_dict())
        self._save_all(events)

    def list_events(self, connector_id: str | None = None) -> list[dict[str, Any]]:
        events = self._load_all()
        if connector_id:
            return [event for event in events if event.get("connector_id") == connector_id]
        return events
