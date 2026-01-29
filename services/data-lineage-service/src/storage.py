from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast


@dataclass
class LineageRecord:
    lineage_id: str
    tenant_id: str
    timestamp: str
    classification: str
    connector: str
    source: dict[str, Any]
    target: dict[str, Any]
    transformations: list[str]
    quality: dict[str, Any] | None
    entity_type: str | None
    entity_payload: dict[str, Any] | None
    metadata: dict[str, Any] | None
    retention_until: str


class LineageStore:
    """JSON-backed lineage store with tenant isolation."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({}))

    def _load(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self.path.read_text()))

    def _save(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2))

    def upsert(self, record: LineageRecord) -> None:
        data = self._load()
        tenant_records = cast(dict[str, Any], data.setdefault(record.tenant_id, {}))
        tenant_records[record.lineage_id] = record.__dict__
        data[record.tenant_id] = tenant_records
        self._save(data)

    def get(self, tenant_id: str, lineage_id: str) -> LineageRecord | None:
        data = self._load()
        tenant_records = cast(dict[str, Any], data.get(tenant_id, {}))
        record = tenant_records.get(lineage_id)
        if not record:
            return None
        return LineageRecord(**cast(dict[str, Any], record))

    def list(self, tenant_id: str) -> list[LineageRecord]:
        data = self._load()
        tenant_records = cast(dict[str, Any], data.get(tenant_id, {}))
        return [LineageRecord(**cast(dict[str, Any], record)) for record in tenant_records.values()]

    def prune_expired(self, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        data = self._load()
        deleted = 0
        for tenant_id in list(data.keys()):
            tenant_records = cast(dict[str, Any], data.get(tenant_id, {}))
            remaining: dict[str, Any] = {}
            for lineage_id, record in tenant_records.items():
                retention_until = record.get("retention_until")
                if retention_until:
                    cutoff = datetime.fromisoformat(retention_until)
                    if cutoff.tzinfo is None:
                        cutoff = cutoff.replace(tzinfo=timezone.utc)
                    if cutoff <= now:
                        deleted += 1
                        continue
                remaining[lineage_id] = record
            data[tenant_id] = remaining
        self._save(data)
        return deleted
