from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast


class TenantStateStore:
    """Simple JSON-backed tenant-scoped state store."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({}))

    def _load(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self.path.read_text()))

    def _save(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2))

    def upsert(self, tenant_id: str, record_id: str, record: dict[str, Any]) -> None:
        data = self._load()
        tenant_records = cast(dict[str, Any], data.setdefault(tenant_id, {}))
        tenant_records[record_id] = record
        data[tenant_id] = tenant_records
        self._save(data)

    def get(self, tenant_id: str, record_id: str) -> dict[str, Any] | None:
        data = self._load()
        tenant_records = cast(dict[str, Any], data.get(tenant_id, {}))
        record = tenant_records.get(record_id)
        if not record:
            return None
        return cast(dict[str, Any], record)

    def delete(self, tenant_id: str, record_id: str) -> None:
        data = self._load()
        tenant_records = cast(dict[str, Any], data.get(tenant_id, {}))
        if record_id in tenant_records:
            tenant_records.pop(record_id)
            data[tenant_id] = tenant_records
            self._save(data)

    def list(self, tenant_id: str) -> list[dict[str, Any]]:
        data = self._load()
        tenant_records = cast(dict[str, Any], data.get(tenant_id, {}))
        return [cast(dict[str, Any], record) for record in tenant_records.values()]

    def tenants(self) -> list[str]:
        data = self._load()
        return list(data.keys())
