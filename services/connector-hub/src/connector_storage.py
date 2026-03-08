from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class ConnectorRecord:
    connector_id: str
    tenant_id: str
    name: str
    version: str
    enabled: bool
    health_status: str
    last_checked: datetime | None
    metadata: dict[str, Any]


class ConnectorStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS connectors (
                    connector_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    health_status TEXT NOT NULL,
                    last_checked TEXT,
                    metadata TEXT NOT NULL
                )
                """)

    def ping(self) -> None:
        with self._connect() as conn:
            conn.execute("SELECT 1")

    def _serialize(self, row: sqlite3.Row) -> ConnectorRecord:
        return ConnectorRecord(
            connector_id=row["connector_id"],
            tenant_id=row["tenant_id"],
            name=row["name"],
            version=row["version"],
            enabled=bool(row["enabled"]),
            health_status=row["health_status"],
            last_checked=(
                datetime.fromisoformat(row["last_checked"]) if row["last_checked"] else None
            ),
            metadata=json.loads(row["metadata"]),
        )

    def create_connector(
        self,
        tenant_id: str,
        name: str,
        version: str,
        metadata: dict[str, Any],
        enabled: bool = True,
    ) -> ConnectorRecord:
        connector_id = str(uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO connectors
                    (connector_id, tenant_id, name, version, enabled, health_status, last_checked, metadata)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    connector_id,
                    tenant_id,
                    name,
                    version,
                    1 if enabled else 0,
                    "unknown",
                    None,
                    json.dumps(metadata),
                ),
            )
        return ConnectorRecord(
            connector_id=connector_id,
            tenant_id=tenant_id,
            name=name,
            version=version,
            enabled=enabled,
            health_status="unknown",
            last_checked=None,
            metadata=metadata,
        )

    def list_connectors(self, tenant_id: str) -> list[ConnectorRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM connectors WHERE tenant_id = ? ORDER BY name", (tenant_id,)
            ).fetchall()
        return [self._serialize(row) for row in rows]

    def get_connector(self, tenant_id: str, connector_id: str) -> ConnectorRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM connectors WHERE tenant_id = ? AND connector_id = ?",
                (tenant_id, connector_id),
            ).fetchone()
        return self._serialize(row) if row else None

    def update_connector(
        self,
        tenant_id: str,
        connector_id: str,
        version: str | None = None,
        enabled: bool | None = None,
        health_status: str | None = None,
    ) -> ConnectorRecord | None:
        record = self.get_connector(tenant_id, connector_id)
        if not record:
            return None
        version = version or record.version
        enabled_value = record.enabled if enabled is None else enabled
        health_status_value = health_status or record.health_status
        last_checked = (
            datetime.now(timezone.utc).isoformat()
            if health_status is not None
            else record.last_checked
        )
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE connectors
                SET version = ?, enabled = ?, health_status = ?, last_checked = ?
                WHERE connector_id = ? AND tenant_id = ?
                """,
                (
                    version,
                    1 if enabled_value else 0,
                    health_status_value,
                    last_checked,
                    connector_id,
                    tenant_id,
                ),
            )
        return self.get_connector(tenant_id, connector_id)
