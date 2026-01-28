from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class AuditActor:
    actor_id: str
    actor_type: str
    roles: list[str]


@dataclass
class AuditResource:
    resource_type: str
    resource_id: str
    metadata: dict[str, Any] | None = None


@dataclass
class AuditEvent:
    event_id: str
    timestamp: datetime
    tenant_id: str
    actor: AuditActor
    action: str
    resource: AuditResource
    outcome: str
    metadata: dict[str, Any] | None = None


class AuditLogStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    actor_type TEXT NOT NULL,
                    actor_roles TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    resource_metadata TEXT,
                    outcome TEXT NOT NULL,
                    metadata TEXT
                )
                """
            )
            conn.commit()

    def record_event(self, event: AuditEvent) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_events (
                    event_id,
                    timestamp,
                    tenant_id,
                    actor_id,
                    actor_type,
                    actor_roles,
                    action,
                    resource_type,
                    resource_id,
                    resource_metadata,
                    outcome,
                    metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.timestamp.isoformat(),
                    event.tenant_id,
                    event.actor.actor_id,
                    event.actor.actor_type,
                    json.dumps(event.actor.roles),
                    event.action,
                    event.resource.resource_type,
                    event.resource.resource_id,
                    json.dumps(event.resource.metadata) if event.resource.metadata else None,
                    event.outcome,
                    json.dumps(event.metadata) if event.metadata else None,
                ),
            )
            conn.commit()

    def list_events(
        self, tenant_id: str, limit: int = 200, offset: int = 0
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    event_id,
                    timestamp,
                    tenant_id,
                    actor_id,
                    actor_type,
                    actor_roles,
                    action,
                    resource_type,
                    resource_id,
                    resource_metadata,
                    outcome,
                    metadata
                FROM audit_events
                WHERE tenant_id = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
                """,
                (tenant_id, limit, offset),
            ).fetchall()
        events: list[dict[str, Any]] = []
        for row in rows:
            events.append(
                {
                    "event_id": row[0],
                    "timestamp": row[1],
                    "tenant_id": row[2],
                    "actor": {
                        "id": row[3],
                        "type": row[4],
                        "roles": json.loads(row[5]) if row[5] else [],
                    },
                    "action": row[6],
                    "resource": {
                        "type": row[7],
                        "id": row[8],
                        "metadata": json.loads(row[9]) if row[9] else None,
                    },
                    "outcome": row[10],
                    "metadata": json.loads(row[11]) if row[11] else None,
                }
            )
        return events


def get_audit_log_store() -> AuditLogStore:
    db_path = Path(os.getenv("AUDIT_LOG_DB_PATH", "data/audit/audit_logs.db"))
    return AuditLogStore(db_path=db_path)


def build_event(
    tenant_id: str,
    actor_id: str,
    actor_type: str,
    roles: list[str],
    action: str,
    resource_type: str,
    resource_id: str,
    outcome: str,
    metadata: dict[str, Any] | None = None,
    resource_metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    return AuditEvent(
        event_id=str(uuid4()),
        timestamp=datetime.now(timezone.utc),
        tenant_id=tenant_id,
        actor=AuditActor(actor_id=actor_id, actor_type=actor_type, roles=roles),
        action=action,
        resource=AuditResource(
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=resource_metadata,
        ),
        outcome=outcome,
        metadata=metadata,
    )
