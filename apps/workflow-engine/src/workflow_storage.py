from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class WorkflowDefinition:
    workflow_id: str
    name: str
    version: str
    owner: str
    description: str | None
    definition: dict[str, Any]
    created_at: str
    updated_at: str


@dataclass
class WorkflowInstance:
    run_id: str
    workflow_id: str
    tenant_id: str
    status: str
    payload: dict[str, Any]
    current_step_id: str | None
    idempotency_key: str | None
    created_at: str
    updated_at: str


@dataclass
class WorkflowStepState:
    run_id: str
    step_id: str
    status: str
    attempts: int
    started_at: str | None
    completed_at: str | None
    error: str | None
    output: dict[str, Any]


@dataclass
class WorkflowEvent:
    event_id: str
    run_id: str
    step_id: str | None
    status: str
    message: str
    created_at: str


@dataclass
class WorkflowApproval:
    approval_id: str
    run_id: str
    step_id: str
    tenant_id: str
    status: str
    created_at: str
    updated_at: str
    decision: str | None
    approver_id: str | None
    comments: str | None
    metadata: dict[str, Any]


@dataclass
class WorkflowJournalEntry:
    journal_id: str
    run_id: str
    step_id: str | None
    phase: str
    status: str
    attempt: int
    details: dict[str, Any]
    created_at: str




@dataclass(frozen=True)
class WorkflowStorageSelection:
    db_path: Path
    backend: str
    durability_mode: str
    source: str


def resolve_workflow_storage(
    *,
    environment: str,
    configured_db_path: str | None = None,
) -> WorkflowStorageSelection:
    from common.env_validation import (
        durability_mode_for_storage,
        enforce_no_default_file_backed_storage,
    )

    default_path = "apps/workflow-engine/storage/workflows.db"
    selected = configured_db_path or os.getenv("WORKFLOW_DB_PATH") or default_path
    used_default = not (configured_db_path or os.getenv("WORKFLOW_DB_PATH"))
    enforce_no_default_file_backed_storage(
        service_name="workflow-engine",
        setting_names=("WORKFLOW_DB_PATH",),
        selected_value=selected,
        used_default=used_default,
        environment=environment,
        remediation_hint=(
            "Provide WORKFLOW_DB_PATH mapped to persistent storage (for example a mounted "
            "volume path) so workflow state survives restarts."
        ),
    )
    return WorkflowStorageSelection(
        db_path=Path(selected),
        backend="sqlite",
        durability_mode=durability_mode_for_storage(selected),
        source="default" if used_default else "explicit",
    )
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
                CREATE TABLE IF NOT EXISTS workflow_definitions (
                    workflow_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    description TEXT,
                    definition TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def ping(self) -> None:
        with self._connect() as conn:
            conn.execute("SELECT 1")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_instances (
                    run_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    current_step_id TEXT,
                    idempotency_key TEXT UNIQUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_step_runs (
                    run_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    error TEXT,
                    output TEXT NOT NULL,
                    PRIMARY KEY (run_id, step_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_events (
                    event_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    step_id TEXT,
                    status TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_approvals (
                    approval_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    decision TEXT,
                    approver_id TEXT,
                    comments TEXT,
                    metadata TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_state_journal (
                    journal_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    step_id TEXT,
                    phase TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            columns = self._columns(conn, "workflow_instances")
            if "current_step_id" not in columns:
                conn.execute("ALTER TABLE workflow_instances ADD COLUMN current_step_id TEXT")
            if "idempotency_key" not in columns:
                conn.execute("ALTER TABLE workflow_instances ADD COLUMN idempotency_key TEXT")
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_workflow_instances_idempotency_key
                ON workflow_instances (idempotency_key)
                """
            )

    @staticmethod
    def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
        cursor = conn.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cursor.fetchall()}

    def upsert_definition(self, workflow_id: str, definition: dict[str, Any]) -> WorkflowDefinition:
        now = datetime.now(timezone.utc).isoformat()
        metadata = definition.get("metadata", {})
        record = WorkflowDefinition(
            workflow_id=workflow_id,
            name=metadata.get("name", workflow_id),
            version=metadata.get("version", "v1"),
            owner=metadata.get("owner", "unknown"),
            description=metadata.get("description"),
            definition=definition,
            created_at=now,
            updated_at=now,
        )
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT workflow_id FROM workflow_definitions WHERE workflow_id = ?",
                (workflow_id,),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE workflow_definitions
                    SET name = ?, version = ?, owner = ?, description = ?, definition = ?, updated_at = ?
                    WHERE workflow_id = ?
                    """,
                    (
                        record.name,
                        record.version,
                        record.owner,
                        record.description,
                        json.dumps(record.definition),
                        record.updated_at,
                        record.workflow_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO workflow_definitions
                    (workflow_id, name, version, owner, description, definition, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.workflow_id,
                        record.name,
                        record.version,
                        record.owner,
                        record.description,
                        json.dumps(record.definition),
                        record.created_at,
                        record.updated_at,
                    ),
                )
        return record

    def get_definition(self, workflow_id: str) -> WorkflowDefinition | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT workflow_id, name, version, owner, description, definition, created_at, updated_at
                FROM workflow_definitions WHERE workflow_id = ?
                """,
                (workflow_id,),
            ).fetchone()
            if not row:
                return None
            return WorkflowDefinition(
                workflow_id=row[0],
                name=row[1],
                version=row[2],
                owner=row[3],
                description=row[4],
                definition=json.loads(row[5]),
                created_at=row[6],
                updated_at=row[7],
            )

    def delete_definition(self, workflow_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM workflow_definitions WHERE workflow_id = ?",
                (workflow_id,),
            )

    def list_definitions(self) -> list[WorkflowDefinition]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT workflow_id, name, version, owner, description, definition, created_at, updated_at
                FROM workflow_definitions ORDER BY name ASC
                """
            ).fetchall()
        return [
            WorkflowDefinition(
                workflow_id=row[0],
                name=row[1],
                version=row[2],
                owner=row[3],
                description=row[4],
                definition=json.loads(row[5]),
                created_at=row[6],
                updated_at=row[7],
            )
            for row in rows
        ]

    def create(
        self,
        run_id: str,
        workflow_id: str,
        tenant_id: str,
        payload: dict[str, Any],
        current_step_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> WorkflowInstance:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            if idempotency_key:
                row = conn.execute(
                    """
                    SELECT run_id, workflow_id, tenant_id, status, payload, current_step_id, idempotency_key, created_at, updated_at
                    FROM workflow_instances WHERE idempotency_key = ?
                    """,
                    (idempotency_key,),
                ).fetchone()
                if row:
                    return self._instance_from_row(row)
            instance = WorkflowInstance(
                run_id=run_id,
                workflow_id=workflow_id,
                tenant_id=tenant_id,
                status="running",
                payload=payload,
                current_step_id=current_step_id,
                idempotency_key=idempotency_key,
                created_at=now,
                updated_at=now,
            )
            conn.execute(
                """
                INSERT INTO workflow_instances (
                    run_id,
                    workflow_id,
                    tenant_id,
                    status,
                    payload,
                    current_step_id,
                    idempotency_key,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    instance.run_id,
                    instance.workflow_id,
                    instance.tenant_id,
                    instance.status,
                    json.dumps(instance.payload),
                    instance.current_step_id,
                    instance.idempotency_key,
                    instance.created_at,
                    instance.updated_at,
                ),
            )
        return instance

    def update_status(
        self, run_id: str, status: str, current_step_id: str | None = None
    ) -> WorkflowInstance | None:
        instance = self.get(run_id)
        if not instance:
            return None
        instance.status = status
        if current_step_id is not None:
            instance.current_step_id = current_step_id
        instance.updated_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE workflow_instances SET status = ?, current_step_id = ?, updated_at = ? WHERE run_id = ?
                """,
                (instance.status, instance.current_step_id, instance.updated_at, instance.run_id),
            )
        return instance

    def get(self, run_id: str) -> WorkflowInstance | None:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT run_id, workflow_id, tenant_id, status, payload, current_step_id, idempotency_key, created_at, updated_at
                FROM workflow_instances WHERE run_id = ?
                """,
                (run_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._instance_from_row(row)

    def list_instances(self, tenant_id: str) -> list[WorkflowInstance]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT run_id, workflow_id, tenant_id, status, payload, current_step_id, idempotency_key, created_at, updated_at
                FROM workflow_instances WHERE tenant_id = ? ORDER BY created_at DESC
                """,
                (tenant_id,),
            ).fetchall()
        return [
            self._instance_from_row(row)
            for row in rows
        ]

    @staticmethod
    def _instance_from_row(row: tuple[Any, ...]) -> WorkflowInstance:
        return WorkflowInstance(
            run_id=row[0],
            workflow_id=row[1],
            tenant_id=row[2],
            status=row[3],
            payload=json.loads(row[4]),
            current_step_id=row[5],
            idempotency_key=row[6],
            created_at=row[7],
            updated_at=row[8],
        )

    def upsert_step_state(
        self, run_id: str, step_id: str, status: str, attempts: int, output: dict[str, Any]
    ) -> WorkflowStepState:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT run_id, step_id, status, attempts, started_at, completed_at, error, output FROM workflow_step_runs WHERE run_id = ? AND step_id = ?",
                (run_id, step_id),
            ).fetchone()
            if existing:
                started_at = existing[4] or now
                completed_at = now if status in {"completed", "failed"} else existing[5]
                conn.execute(
                    """
                    UPDATE workflow_step_runs
                    SET status = ?, attempts = ?, started_at = ?, completed_at = ?, error = ?, output = ?
                    WHERE run_id = ? AND step_id = ?
                    """,
                    (
                        status,
                        attempts,
                        started_at,
                        completed_at,
                        existing[6],
                        json.dumps(output),
                        run_id,
                        step_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO workflow_step_runs
                    (run_id, step_id, status, attempts, started_at, completed_at, error, output)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        step_id,
                        status,
                        attempts,
                        now,
                        now if status in {"completed", "failed"} else None,
                        None,
                        json.dumps(output),
                    ),
                )
        state = self.get_step_state(run_id, step_id)
        if not state:
            raise RuntimeError("Failed to persist step state")
        return state

    def update_step_error(self, run_id: str, step_id: str, error: str) -> WorkflowStepState:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE workflow_step_runs
                SET status = ?, completed_at = ?, error = ?
                WHERE run_id = ? AND step_id = ?
                """,
                ("failed", now, error, run_id, step_id),
            )
        state = self.get_step_state(run_id, step_id)
        if not state:
            raise RuntimeError("Failed to update step state")
        return state

    def get_step_state(self, run_id: str, step_id: str) -> WorkflowStepState | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT run_id, step_id, status, attempts, started_at, completed_at, error, output
                FROM workflow_step_runs WHERE run_id = ? AND step_id = ?
                """,
                (run_id, step_id),
            ).fetchone()
            if not row:
                return None
            return WorkflowStepState(
                run_id=row[0],
                step_id=row[1],
                status=row[2],
                attempts=row[3],
                started_at=row[4],
                completed_at=row[5],
                error=row[6],
                output=json.loads(row[7]),
            )

    def list_step_states(self, run_id: str) -> list[WorkflowStepState]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT run_id, step_id, status, attempts, started_at, completed_at, error, output
                FROM workflow_step_runs WHERE run_id = ? ORDER BY started_at ASC
                """,
                (run_id,),
            ).fetchall()
        return [
            WorkflowStepState(
                run_id=row[0],
                step_id=row[1],
                status=row[2],
                attempts=row[3],
                started_at=row[4],
                completed_at=row[5],
                error=row[6],
                output=json.loads(row[7]),
            )
            for row in rows
        ]

    def add_event(
        self, run_id: str, status: str, message: str, step_id: str | None = None
    ) -> WorkflowEvent:
        now = datetime.now(timezone.utc).isoformat()
        event_id = f"event_{run_id}_{now}"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workflow_events (event_id, run_id, step_id, status, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_id, run_id, step_id, status, message, now),
            )
        return WorkflowEvent(
            event_id=event_id,
            run_id=run_id,
            step_id=step_id,
            status=status,
            message=message,
            created_at=now,
        )

    def list_events(self, run_id: str) -> list[WorkflowEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT event_id, run_id, step_id, status, message, created_at
                FROM workflow_events WHERE run_id = ? ORDER BY created_at ASC
                """,
                (run_id,),
            ).fetchall()
        return [
            WorkflowEvent(
                event_id=row[0],
                run_id=row[1],
                step_id=row[2],
                status=row[3],
                message=row[4],
                created_at=row[5],
            )
            for row in rows
        ]

    def upsert_approval(
        self,
        approval_id: str,
        run_id: str,
        step_id: str,
        tenant_id: str,
        status: str,
        metadata: dict[str, Any],
        decision: str | None = None,
        approver_id: str | None = None,
        comments: str | None = None,
    ) -> WorkflowApproval:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT approval_id FROM workflow_approvals WHERE approval_id = ?",
                (approval_id,),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE workflow_approvals
                    SET status = ?, updated_at = ?, decision = ?, approver_id = ?, comments = ?, metadata = ?
                    WHERE approval_id = ?
                    """,
                    (
                        status,
                        now,
                        decision,
                        approver_id,
                        comments,
                        json.dumps(metadata),
                        approval_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO workflow_approvals
                    (approval_id, run_id, step_id, tenant_id, status, created_at, updated_at, decision, approver_id, comments, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        approval_id,
                        run_id,
                        step_id,
                        tenant_id,
                        status,
                        now,
                        now,
                        decision,
                        approver_id,
                        comments,
                        json.dumps(metadata),
                    ),
                )
        approval = self.get_approval(approval_id)
        if not approval:
            raise RuntimeError("Approval record was not persisted.")
        return approval

    def get_approval(self, approval_id: str) -> WorkflowApproval | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT approval_id, run_id, step_id, tenant_id, status, created_at, updated_at, decision, approver_id, comments, metadata
                FROM workflow_approvals WHERE approval_id = ?
                """,
                (approval_id,),
            ).fetchone()
            if not row:
                return None
            return WorkflowApproval(
                approval_id=row[0],
                run_id=row[1],
                step_id=row[2],
                tenant_id=row[3],
                status=row[4],
                created_at=row[5],
                updated_at=row[6],
                decision=row[7],
                approver_id=row[8],
                comments=row[9],
                metadata=json.loads(row[10]),
            )

    def list_approvals(self, tenant_id: str, status: str | None = None) -> list[WorkflowApproval]:
        query = """
            SELECT approval_id, run_id, step_id, tenant_id, status, created_at, updated_at, decision, approver_id, comments, metadata
            FROM workflow_approvals WHERE tenant_id = ?
        """
        params: list[Any] = [tenant_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            WorkflowApproval(
                approval_id=row[0],
                run_id=row[1],
                step_id=row[2],
                tenant_id=row[3],
                status=row[4],
                created_at=row[5],
                updated_at=row[6],
                decision=row[7],
                approver_id=row[8],
                comments=row[9],
                metadata=json.loads(row[10]),
            )
            for row in rows
        ]

    def find_approval_for_step(self, run_id: str, step_id: str) -> WorkflowApproval | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT approval_id, run_id, step_id, tenant_id, status, created_at, updated_at, decision, approver_id, comments, metadata
                FROM workflow_approvals WHERE run_id = ? AND step_id = ?
                """,
                (run_id, step_id),
            ).fetchone()
            if not row:
                return None
            return WorkflowApproval(
                approval_id=row[0],
                run_id=row[1],
                step_id=row[2],
                tenant_id=row[3],
                status=row[4],
                created_at=row[5],
                updated_at=row[6],
                decision=row[7],
                approver_id=row[8],
                comments=row[9],
                metadata=json.loads(row[10]),
            )

    def add_journal_entry(
        self,
        run_id: str,
        phase: str,
        status: str,
        attempt: int,
        details: dict[str, Any] | None = None,
        step_id: str | None = None,
    ) -> WorkflowJournalEntry:
        now = datetime.now(timezone.utc).isoformat()
        journal_id = f"journal_{run_id}_{phase}_{status}_{attempt}_{now}"
        payload = details or {}
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workflow_state_journal (
                    journal_id, run_id, step_id, phase, status, attempt, details, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (journal_id, run_id, step_id, phase, status, attempt, json.dumps(payload), now),
            )
        return WorkflowJournalEntry(
            journal_id=journal_id,
            run_id=run_id,
            step_id=step_id,
            phase=phase,
            status=status,
            attempt=attempt,
            details=payload,
            created_at=now,
        )

    def list_journal_entries(
        self, run_id: str, phase: str | None = None, step_id: str | None = None
    ) -> list[WorkflowJournalEntry]:
        query = (
            "SELECT journal_id, run_id, step_id, phase, status, attempt, details, created_at "
            "FROM workflow_state_journal WHERE run_id = ?"
        )
        params: list[Any] = [run_id]
        if phase:
            query += " AND phase = ?"
            params.append(phase)
        if step_id:
            query += " AND step_id = ?"
            params.append(step_id)
        query += " ORDER BY created_at ASC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            WorkflowJournalEntry(
                journal_id=row[0],
                run_id=row[1],
                step_id=row[2],
                phase=row[3],
                status=row[4],
                attempt=row[5],
                details=json.loads(row[6]),
                created_at=row[7],
            )
            for row in rows
        ]
