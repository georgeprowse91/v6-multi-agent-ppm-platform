from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


class HealthSnapshotStore:
    def __init__(self, path: Path, history_limit: int = 20) -> None:
        self.path = path
        self.history_limit = history_limit
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({}))

    def _load(self) -> dict[str, Any]:
        return json.loads(self.path.read_text())

    def _save(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2))

    def list_snapshots(self, tenant_id: str, project_id: str) -> list[dict[str, Any]]:
        data = self._load()
        tenant_records = data.get(tenant_id, {})
        project_records = tenant_records.get(project_id, [])
        snapshots = [
            snapshot
            for snapshot in project_records
            if isinstance(snapshot, dict) and snapshot.get("project_id") == project_id
        ]
        return sorted(
            snapshots, key=lambda snapshot: _parse_timestamp(snapshot.get("monitored_at"))
        )

    def add_snapshot(
        self, tenant_id: str, project_id: str, snapshot: dict[str, Any]
    ) -> list[dict[str, Any]]:
        data = self._load()
        tenant_records = data.setdefault(tenant_id, {})
        project_records = tenant_records.get(project_id, [])
        if not isinstance(project_records, list):
            project_records = []
        monitored_at = snapshot.get("monitored_at")
        filtered = [
            record
            for record in project_records
            if isinstance(record, dict) and record.get("monitored_at") != monitored_at
        ]
        filtered.append(snapshot)
        filtered = sorted(filtered, key=lambda item: _parse_timestamp(item.get("monitored_at")))
        if self.history_limit > 0:
            filtered = filtered[-self.history_limit :]
        tenant_records[project_id] = filtered
        data[tenant_id] = tenant_records
        self._save(data)
        return filtered
