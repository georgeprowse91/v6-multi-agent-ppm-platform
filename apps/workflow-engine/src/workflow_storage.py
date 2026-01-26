from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class WorkflowInstance:
    run_id: str
    workflow_id: str
    tenant_id: str
    status: str
    payload: dict[str, Any]
    created_at: str
    updated_at: str


class WorkflowStore:
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
                CREATE TABLE IF NOT EXISTS workflow_instances (
                    run_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create(
        self, run_id: str, workflow_id: str, tenant_id: str, payload: dict[str, Any]
    ) -> WorkflowInstance:
        now = datetime.now(timezone.utc).isoformat()
        instance = WorkflowInstance(
            run_id=run_id,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            status="running",
            payload=payload,
            created_at=now,
            updated_at=now,
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workflow_instances (run_id, workflow_id, tenant_id, status, payload, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    instance.run_id,
                    instance.workflow_id,
                    instance.tenant_id,
                    instance.status,
                    json.dumps(instance.payload),
                    instance.created_at,
                    instance.updated_at,
                ),
            )
        return instance

    def update_status(self, run_id: str, status: str) -> WorkflowInstance | None:
        instance = self.get(run_id)
        if not instance:
            return None
        instance.status = status
        instance.updated_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE workflow_instances SET status = ?, updated_at = ? WHERE run_id = ?
                """,
                (instance.status, instance.updated_at, instance.run_id),
            )
        return instance

    def get(self, run_id: str) -> WorkflowInstance | None:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT run_id, workflow_id, tenant_id, status, payload, created_at, updated_at FROM workflow_instances WHERE run_id = ?",
                (run_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return WorkflowInstance(
                run_id=row[0],
                workflow_id=row[1],
                tenant_id=row[2],
                status=row[3],
                payload=json.loads(row[4]),
                created_at=row[5],
                updated_at=row[6],
            )
