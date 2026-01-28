from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast
from uuid import uuid4


@dataclass
class SyncLogRecord:
    log_id: str
    connector: str
    entity: str
    status: str
    latency_ms: int
    errors: list[str]
    last_sync_at: str
    created_at: str
    details: dict[str, Any]


class SyncLogStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps([]))

    def _load(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], json.loads(self.path.read_text()))

    def _save(self, data: list[dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(data, indent=2))

    def append(self, record: SyncLogRecord) -> None:
        data = self._load()
        data.append(record.__dict__)
        self._save(data)

    def create(
        self,
        *,
        connector: str,
        entity: str,
        status: str,
        latency_ms: int,
        errors: list[str] | None = None,
        last_sync_at: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> SyncLogRecord:
        now = datetime.now(timezone.utc).isoformat()
        record = SyncLogRecord(
            log_id=str(uuid4()),
            connector=connector,
            entity=entity,
            status=status,
            latency_ms=latency_ms,
            errors=errors or [],
            last_sync_at=last_sync_at or now,
            created_at=now,
            details=details or {},
        )
        self.append(record)
        return record

    def list_recent(self, limit: int = 100) -> list[SyncLogRecord]:
        data = self._load()
        recent = data[-limit:]
        return [SyncLogRecord(**item) for item in reversed(recent)]

    def summary(self, connector: str | None = None) -> dict[str, Any]:
        data = self._load()
        if connector:
            data = [item for item in data if item.get("connector") == connector]
        total = len(data)
        success = len([item for item in data if item.get("status") == "success"])
        errors = len([item for item in data if item.get("status") == "error"])
        last_sync_at = None
        if data:
            last_sync_at = max(item.get("last_sync_at", "") for item in data)
        return {
            "total_runs": total,
            "success_runs": success,
            "error_runs": errors,
            "success_rate": (success / total) if total else 0.0,
            "last_sync_at": last_sync_at,
        }


def get_sync_log_store() -> SyncLogStore:
    path = Path(
        os.getenv(
            "DATA_SYNC_LOG_PATH",
            "services/data-sync-service/storage/sync_logs.json",
        )
    )
    return SyncLogStore(path)
