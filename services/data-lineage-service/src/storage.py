from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
    work_item_id: str | None = None


class LineageStore:
    """SQLite-backed lineage store with tenant isolation."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lineage_events (
                    lineage_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    connector_id TEXT NOT NULL,
                    work_item_id TEXT,
                    source_entity TEXT NOT NULL,
                    target_entity TEXT NOT NULL,
                    transformations TEXT NOT NULL,
                    entity_type TEXT,
                    entity_payload TEXT,
                    quality TEXT,
                    classification TEXT NOT NULL,
                    metadata TEXT,
                    timestamp TEXT NOT NULL,
                    retention_until TEXT NOT NULL
                )
                """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_lineage_events_tenant_id ON lineage_events(tenant_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_lineage_events_connector_id ON lineage_events(connector_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_lineage_events_work_item_id ON lineage_events(work_item_id)"
            )

    def ping(self) -> None:
        with self._connect() as conn:
            conn.execute("SELECT 1")

    def _serialize(self, value: dict[str, Any] | list[str] | None) -> str | None:
        if value is None:
            return None
        return json.dumps(value)

    def _deserialize(self, value: str | None) -> dict[str, Any] | list[str] | None:
        if value is None:
            return None
        return json.loads(value)

    def upsert(self, record: LineageRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO lineage_events (
                    lineage_id,
                    tenant_id,
                    connector_id,
                    work_item_id,
                    source_entity,
                    target_entity,
                    transformations,
                    entity_type,
                    entity_payload,
                    quality,
                    classification,
                    metadata,
                    timestamp,
                    retention_until
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.lineage_id,
                    record.tenant_id,
                    record.connector,
                    record.work_item_id,
                    self._serialize(record.source),
                    self._serialize(record.target),
                    self._serialize(record.transformations) or "[]",
                    record.entity_type,
                    self._serialize(record.entity_payload),
                    self._serialize(record.quality),
                    record.classification,
                    self._serialize(record.metadata),
                    record.timestamp,
                    record.retention_until,
                ),
            )

    def get(self, tenant_id: str, lineage_id: str) -> LineageRecord | None:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM lineage_events
                WHERE tenant_id = ? AND lineage_id = ?
                """,
                (tenant_id, lineage_id),
            )
            row = cursor.fetchone()
        return self._row_to_record(row) if row else None

    def list(
        self, tenant_id: str, connector_id: str | None = None, work_item_id: str | None = None
    ) -> list[LineageRecord]:
        clauses = ["tenant_id = ?"]
        values: list[str] = [tenant_id]
        if connector_id:
            clauses.append("connector_id = ?")
            values.append(connector_id)
        if work_item_id:
            clauses.append("work_item_id = ?")
            values.append(work_item_id)
        where_clause = " AND ".join(clauses)
        query = f"SELECT * FROM lineage_events WHERE {where_clause} ORDER BY timestamp DESC"
        with self._connect() as conn:
            cursor = conn.execute(query, values)
            rows = cursor.fetchall()
        return [self._row_to_record(row) for row in rows]

    def prune_expired(self, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        deleted = 0
        with self._connect() as conn:
            cursor = conn.execute("SELECT * FROM lineage_events")
            records = [self._row_to_record(row) for row in cursor.fetchall()]

        remaining: list[LineageRecord] = []
        for record in records:
            retention_until = record.retention_until
            if retention_until:
                cutoff = datetime.fromisoformat(retention_until)
                if cutoff.tzinfo is None:
                    cutoff = cutoff.replace(tzinfo=timezone.utc)
                if cutoff <= now:
                    deleted += 1
                    continue
            remaining.append(record)

        with self._connect() as conn:
            conn.execute("DELETE FROM lineage_events")
            for record in remaining:
                self.upsert(record)
        return deleted

    def _row_to_record(self, row: sqlite3.Row) -> LineageRecord:
        return LineageRecord(
            lineage_id=row["lineage_id"],
            tenant_id=row["tenant_id"],
            connector=row["connector_id"],
            work_item_id=row["work_item_id"],
            source=self._deserialize(row["source_entity"]) or {},
            target=self._deserialize(row["target_entity"]) or {},
            transformations=self._deserialize(row["transformations"]) or [],
            entity_type=row["entity_type"],
            entity_payload=self._deserialize(row["entity_payload"]),
            quality=self._deserialize(row["quality"]),
            classification=row["classification"],
            metadata=self._deserialize(row["metadata"]),
            timestamp=row["timestamp"],
            retention_until=row["retention_until"],
        )
