from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast


@dataclass
class TaskRecord:
    task_id: str
    title: str
    status: str
    external_id: str | None
    updated_at: str
    created_at: str
    source: str
    details: dict[str, Any]


class TaskStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({}))

    def _load(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self.path.read_text()))

    def _save(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2))

    def upsert(self, task_id: str, payload: dict[str, Any]) -> TaskRecord:
        now = datetime.now(timezone.utc).isoformat()
        data = self._load()
        existing = data.get(task_id)
        if existing:
            created_at = existing.get("created_at", now)
        else:
            created_at = now
        record = {
            "task_id": task_id,
            "title": payload.get("title", ""),
            "status": payload.get("status", "open"),
            "external_id": payload.get("external_id"),
            "updated_at": payload.get("updated_at", now),
            "created_at": created_at,
            "source": payload.get("source", "internal"),
            "details": payload.get("details", {}),
        }
        data[task_id] = record
        self._save(data)
        return TaskRecord(**record)

    def get(self, task_id: str) -> TaskRecord | None:
        data = self._load()
        record = data.get(task_id)
        if not record:
            return None
        return TaskRecord(**record)

    def list_all(self) -> list[TaskRecord]:
        data = self._load()
        return [TaskRecord(**item) for item in data.values()]


def get_task_store() -> TaskStore:
    path = Path(
        os.getenv(
            "DATA_SYNC_TASKS_PATH",
            "services/data-sync-service/storage/tasks.json",
        )
    )
    return TaskStore(path)
