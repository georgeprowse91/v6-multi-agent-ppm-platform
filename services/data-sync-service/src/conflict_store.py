from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast
from uuid import uuid4


@dataclass
class ConflictRecord:
    conflict_id: str
    connector: str
    entity: str
    task_id: str | None
    external_id: str | None
    strategy: str
    reason: str
    internal_updated_at: str | None
    external_updated_at: str | None
    created_at: str
    details: dict[str, Any]


class ConflictStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps([]))

    def _load(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], json.loads(self.path.read_text()))

    def _save(self, data: list[dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(data, indent=2))

    def record(
        self,
        *,
        connector: str,
        entity: str,
        task_id: str | None,
        external_id: str | None,
        strategy: str,
        reason: str,
        internal_updated_at: str | None,
        external_updated_at: str | None,
        details: dict[str, Any] | None = None,
    ) -> ConflictRecord:
        record = ConflictRecord(
            conflict_id=str(uuid4()),
            connector=connector,
            entity=entity,
            task_id=task_id,
            external_id=external_id,
            strategy=strategy,
            reason=reason,
            internal_updated_at=internal_updated_at,
            external_updated_at=external_updated_at,
            created_at=datetime.now(timezone.utc).isoformat(),
            details=details or {},
        )
        data = self._load()
        data.append(record.__dict__)
        self._save(data)
        return record

    def list_recent(self, limit: int = 50) -> list[ConflictRecord]:
        data = self._load()
        recent = data[-limit:]
        return [ConflictRecord(**item) for item in reversed(recent)]


def get_conflict_store() -> ConflictStore:
    path = Path(
        os.getenv(
            "DATA_SYNC_CONFLICT_PATH",
            "services/data-sync-service/storage/conflicts.json",
        )
    )
    return ConflictStore(path)
