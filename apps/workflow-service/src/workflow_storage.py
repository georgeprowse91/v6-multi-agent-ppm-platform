from __future__ import annotations

import json
import os
import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

try:
    import psycopg2
    import psycopg2.extras
except Exception:  # pragma: no cover - optional dependency in some environments
    psycopg2 = None  # type: ignore[assignment]


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
    connection_url: str | None = None


@runtime_checkable
class WorkflowInstanceRepository(Protocol):
    def create(
        self,
        run_id: str,
        workflow_id: str,
        tenant_id: str,
        payload: dict[str, Any],
        current_step_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> WorkflowInstance: ...

    def get(self, run_id: str) -> WorkflowInstance | None: ...

    def update_status(
        self, run_id: str, status: str, current_step_id: str | None = None
    ) -> WorkflowInstance | None: ...


@runtime_checkable
class WorkflowEventRepository(Protocol):
    def add_event(
        self, run_id: str, status: str, message: str, step_id: str | None = None
    ) -> WorkflowEvent: ...


@runtime_checkable
class WorkflowApprovalRepository(Protocol):
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
    ) -> WorkflowApproval: ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_workflow_storage(
    *,
    environment: str,
    configured_db_path: str | None = None,
) -> WorkflowStorageSelection:
    from common.env_validation import (
        durability_mode_for_storage,
        enforce_no_default_file_backed_storage,
    )

    connection_url = os.getenv("WORKFLOW_DB_URL")
    if connection_url:
        return WorkflowStorageSelection(
            db_path=Path(":memory:"),
            backend="postgresql",
            durability_mode="network",
            source="explicit",
            connection_url=connection_url,
        )

    default_path = "apps/workflow-service/storage/workflows.db"
    selected = configured_db_path or os.getenv("WORKFLOW_DB_PATH") or default_path
    used_default = not (configured_db_path or os.getenv("WORKFLOW_DB_PATH"))
    enforce_no_default_file_backed_storage(
        service_name="workflow-service",
        setting_names=("WORKFLOW_DB_PATH", "WORKFLOW_DB_URL"),
        selected_value=selected,
        used_default=used_default,
        environment=environment,
        remediation_hint=(
            "Provide WORKFLOW_DB_PATH mapped to persistent storage (for example a mounted "
            "volume path) or configure WORKFLOW_DB_URL for managed SQL."
        ),
    )
    return WorkflowStorageSelection(
        db_path=Path(selected),
        backend="sqlite",
        durability_mode=durability_mode_for_storage(selected),
        source="default" if used_default else "explicit",
    )


class WorkflowStore:
    def __init__(self, db_path: Path | None = None, *, connection_url: str | None = None) -> None:
        self.db_path = db_path or Path(":memory:")
        self.connection_url = connection_url
        self.backend = "postgresql" if connection_url else "sqlite"
        if self.backend == "sqlite":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    @classmethod
    def from_selection(cls, selection: WorkflowStorageSelection) -> WorkflowStore:
        return cls(db_path=selection.db_path, connection_url=selection.connection_url)

    def _connect(self) -> Any:
        if self.backend == "sqlite":
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            return conn
        if psycopg2 is None:
            raise RuntimeError("psycopg2 is required for PostgreSQL workflow storage")
        return psycopg2.connect(self.connection_url)

    @contextmanager
    def _transaction(self) -> Iterator[Any]:
        conn = self._connect()
        try:
            if self.backend == "sqlite":
                conn.execute("BEGIN IMMEDIATE")
            else:
                conn.autocommit = False
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _execute_migration(self, conn: Any, sql: str) -> None:
        if self.backend == "sqlite":
            conn.executescript(sql)
        else:
            with conn.cursor() as cur:
                cur.execute(sql)

    def _ensure_schema(self) -> None:
        migration = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "sql"
            / f"001_init_{self.backend}.sql"
        )
        sql = migration.read_text(encoding="utf-8")
        with self._connect() as conn:
            self._execute_migration(conn, sql)
            conn.commit()

    def ping(self) -> None:
        with self._connect() as conn:
            if self.backend == "sqlite":
                conn.execute("SELECT 1")
            else:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")

    def _fetchone(self, conn: Any, query: str, params: tuple[Any, ...]) -> Any:
        if self.backend == "sqlite":
            return conn.execute(query, params).fetchone()
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()

    def _fetchall(self, conn: Any, query: str, params: tuple[Any, ...] = ()) -> list[Any]:
        if self.backend == "sqlite":
            return conn.execute(query, params).fetchall()
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def _execute(self, conn: Any, query: str, params: tuple[Any, ...]) -> None:
        if self.backend == "sqlite":
            conn.execute(query, params)
        else:
            with conn.cursor() as cur:
                cur.execute(query, params)

    def _row(self, row: Any, idx: int) -> Any:
        return row[idx] if not hasattr(row, "keys") else row[idx]

    def upsert_definition(self, workflow_id: str, definition: dict[str, Any]) -> WorkflowDefinition:
        metadata = definition.get("metadata", {})
        now = _now()
        record = WorkflowDefinition(
            workflow_id=workflow_id,
            name=metadata.get("name", workflow_id),
            version=str(metadata.get("version", "1.0.0")),
            owner=metadata.get("owner", "unknown"),
            description=metadata.get("description"),
            definition=definition,
            created_at=now,
            updated_at=now,
        )
        with self._transaction() as conn:
            row = self._fetchone(
                conn,
                (
                    "SELECT workflow_id, created_at FROM workflow_definitions WHERE workflow_id = %s"
                    if self.backend == "postgresql"
                    else "SELECT workflow_id, created_at FROM workflow_definitions WHERE workflow_id = ?"
                ),
                (workflow_id,),
            )
            if row:
                created_at = row[1]
                self._execute(
                    conn,
                    """
                    UPDATE workflow_definitions
                    SET name = {p1}, version = {p1}, owner = {p1}, description = {p1}, definition = {p1}, updated_at = {p1}
                    WHERE workflow_id = {p1}
                    """.replace("{p1}", "%s" if self.backend == "postgresql" else "?"),
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
                record.created_at = created_at
            else:
                self._execute(
                    conn,
                    """
                    INSERT INTO workflow_definitions
                    (workflow_id, name, version, owner, description, definition, created_at, updated_at)
                    VALUES ({p1}, {p1}, {p1}, {p1}, {p1}, {p1}, {p1}, {p1})
                    """.replace("{p1}", "%s" if self.backend == "postgresql" else "?"),
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
            row = self._fetchone(
                conn,
                (
                    "SELECT workflow_id, name, version, owner, description, definition, created_at, updated_at FROM workflow_definitions WHERE workflow_id = %s"
                    if self.backend == "postgresql"
                    else "SELECT workflow_id, name, version, owner, description, definition, created_at, updated_at FROM workflow_definitions WHERE workflow_id = ?"
                ),
                (workflow_id,),
            )
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
        with self._transaction() as conn:
            self._execute(
                conn,
                (
                    "DELETE FROM workflow_definitions WHERE workflow_id = %s"
                    if self.backend == "postgresql"
                    else "DELETE FROM workflow_definitions WHERE workflow_id = ?"
                ),
                (workflow_id,),
            )

    def list_definitions(self) -> list[WorkflowDefinition]:
        with self._connect() as conn:
            rows = self._fetchall(
                conn,
                "SELECT workflow_id, name, version, owner, description, definition, created_at, updated_at FROM workflow_definitions ORDER BY name ASC",
            )
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
        now = _now()
        with self._transaction() as conn:
            if idempotency_key:
                existing = self._fetchone(
                    conn,
                    (
                        "SELECT run_id, workflow_id, tenant_id, status, payload, current_step_id, idempotency_key, created_at, updated_at FROM workflow_instances WHERE idempotency_key = %s"
                        if self.backend == "postgresql"
                        else "SELECT run_id, workflow_id, tenant_id, status, payload, current_step_id, idempotency_key, created_at, updated_at FROM workflow_instances WHERE idempotency_key = ?"
                    ),
                    (idempotency_key,),
                )
                if existing:
                    return self._instance_from_row(existing)
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
            self._execute(
                conn,
                """
                INSERT INTO workflow_instances
                (run_id, workflow_id, tenant_id, status, payload, current_step_id, idempotency_key, created_at, updated_at)
                VALUES ({p1}, {p1}, {p1}, {p1}, {p1}, {p1}, {p1}, {p1}, {p1})
                """.replace("{p1}", "%s" if self.backend == "postgresql" else "?"),
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
        with self._transaction() as conn:
            row = self._fetchone(
                conn,
                (
                    "SELECT run_id, workflow_id, tenant_id, status, payload, current_step_id, idempotency_key, created_at, updated_at FROM workflow_instances WHERE run_id = %s FOR UPDATE"
                    if self.backend == "postgresql"
                    else "SELECT run_id, workflow_id, tenant_id, status, payload, current_step_id, idempotency_key, created_at, updated_at FROM workflow_instances WHERE run_id = ?"
                ),
                (run_id,),
            )
            if not row:
                return None
            instance = self._instance_from_row(row)
            instance.status = status
            if current_step_id is not None:
                instance.current_step_id = current_step_id
            instance.updated_at = _now()
            self._execute(
                conn,
                "UPDATE workflow_instances SET status = {p}, current_step_id = {p}, updated_at = {p} WHERE run_id = {p}".replace(
                    "{p}", "%s" if self.backend == "postgresql" else "?"
                ),
                (instance.status, instance.current_step_id, instance.updated_at, instance.run_id),
            )
        return instance

    def get(self, run_id: str) -> WorkflowInstance | None:
        with self._connect() as conn:
            row = self._fetchone(
                conn,
                (
                    "SELECT run_id, workflow_id, tenant_id, status, payload, current_step_id, idempotency_key, created_at, updated_at FROM workflow_instances WHERE run_id = %s"
                    if self.backend == "postgresql"
                    else "SELECT run_id, workflow_id, tenant_id, status, payload, current_step_id, idempotency_key, created_at, updated_at FROM workflow_instances WHERE run_id = ?"
                ),
                (run_id,),
            )
            return self._instance_from_row(row) if row else None

    def list_instances(self, tenant_id: str) -> list[WorkflowInstance]:
        with self._connect() as conn:
            rows = self._fetchall(
                conn,
                "SELECT run_id, workflow_id, tenant_id, status, payload, current_step_id, idempotency_key, created_at, updated_at FROM workflow_instances WHERE tenant_id = {p} ORDER BY created_at DESC".replace(
                    "{p}", "%s" if self.backend == "postgresql" else "?"
                ),
                (tenant_id,),
            )
        return [self._instance_from_row(row) for row in rows]

    @staticmethod
    def _instance_from_row(row: Any) -> WorkflowInstance:
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
        now = _now()
        with self._transaction() as conn:
            existing = self._fetchone(
                conn,
                "SELECT run_id, step_id, status, attempts, started_at, completed_at, error, output FROM workflow_step_runs WHERE run_id = {p} AND step_id = {p}".replace(
                    "{p}", "%s" if self.backend == "postgresql" else "?"
                ),
                (run_id, step_id),
            )
            if existing:
                started_at = existing[4] or now
                completed_at = now if status in {"completed", "failed"} else existing[5]
                self._execute(
                    conn,
                    "UPDATE workflow_step_runs SET status = {p}, attempts = {p}, started_at = {p}, completed_at = {p}, error = {p}, output = {p} WHERE run_id = {p} AND step_id = {p}".replace(
                        "{p}", "%s" if self.backend == "postgresql" else "?"
                    ),
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
                self._execute(
                    conn,
                    "INSERT INTO workflow_step_runs (run_id, step_id, status, attempts, started_at, completed_at, error, output) VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})".replace(
                        "{p}", "%s" if self.backend == "postgresql" else "?"
                    ),
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
        now = _now()
        with self._transaction() as conn:
            self._execute(
                conn,
                "UPDATE workflow_step_runs SET status = {p}, completed_at = {p}, error = {p} WHERE run_id = {p} AND step_id = {p}".replace(
                    "{p}", "%s" if self.backend == "postgresql" else "?"
                ),
                ("failed", now, error, run_id, step_id),
            )
        state = self.get_step_state(run_id, step_id)
        if not state:
            raise RuntimeError("Failed to update step state")
        return state

    def get_step_state(self, run_id: str, step_id: str) -> WorkflowStepState | None:
        with self._connect() as conn:
            row = self._fetchone(
                conn,
                "SELECT run_id, step_id, status, attempts, started_at, completed_at, error, output FROM workflow_step_runs WHERE run_id = {p} AND step_id = {p}".replace(
                    "{p}", "%s" if self.backend == "postgresql" else "?"
                ),
                (run_id, step_id),
            )
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
            rows = self._fetchall(
                conn,
                "SELECT run_id, step_id, status, attempts, started_at, completed_at, error, output FROM workflow_step_runs WHERE run_id = {p} ORDER BY step_id ASC".replace(
                    "{p}", "%s" if self.backend == "postgresql" else "?"
                ),
                (run_id,),
            )
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
        created_at = _now()
        event_id = f"event_{run_id}_{status}_{created_at}"
        with self._transaction() as conn:
            self._execute(
                conn,
                (
                    "INSERT OR IGNORE INTO workflow_events (event_id, run_id, step_id, status, message, created_at) VALUES (?, ?, ?, ?, ?, ?)"
                    if self.backend == "sqlite"
                    else "INSERT INTO workflow_events (event_id, run_id, step_id, status, message, created_at) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (event_id) DO NOTHING"
                ),
                (event_id, run_id, step_id, status, message, created_at),
            )
        return WorkflowEvent(
            event_id=event_id,
            run_id=run_id,
            step_id=step_id,
            status=status,
            message=message,
            created_at=created_at,
        )

    def list_events(self, run_id: str) -> list[WorkflowEvent]:
        with self._connect() as conn:
            rows = self._fetchall(
                conn,
                "SELECT event_id, run_id, step_id, status, message, created_at FROM workflow_events WHERE run_id = {p} ORDER BY created_at ASC".replace(
                    "{p}", "%s" if self.backend == "postgresql" else "?"
                ),
                (run_id,),
            )
        return [
            WorkflowEvent(
                event_id=r[0], run_id=r[1], step_id=r[2], status=r[3], message=r[4], created_at=r[5]
            )
            for r in rows
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
        now = _now()
        with self._transaction() as conn:
            existing = self._fetchone(
                conn,
                (
                    "SELECT approval_id, run_id, step_id, tenant_id, status, created_at, updated_at, decision, approver_id, comments, metadata FROM workflow_approvals WHERE approval_id = %s FOR UPDATE"
                    if self.backend == "postgresql"
                    else "SELECT approval_id, run_id, step_id, tenant_id, status, created_at, updated_at, decision, approver_id, comments, metadata FROM workflow_approvals WHERE approval_id = ?"
                ),
                (approval_id,),
            )
            if existing and existing[4] != "pending" and status != existing[4]:
                return WorkflowApproval(
                    approval_id=existing[0],
                    run_id=existing[1],
                    step_id=existing[2],
                    tenant_id=existing[3],
                    status=existing[4],
                    created_at=existing[5],
                    updated_at=existing[6],
                    decision=existing[7],
                    approver_id=existing[8],
                    comments=existing[9],
                    metadata=json.loads(existing[10]),
                )
            if existing:
                self._execute(
                    conn,
                    "UPDATE workflow_approvals SET status = {p}, updated_at = {p}, decision = {p}, approver_id = {p}, comments = {p}, metadata = {p} WHERE approval_id = {p}".replace(
                        "{p}", "%s" if self.backend == "postgresql" else "?"
                    ),
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
                self._execute(
                    conn,
                    "INSERT INTO workflow_approvals (approval_id, run_id, step_id, tenant_id, status, created_at, updated_at, decision, approver_id, comments, metadata) VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})".replace(
                        "{p}", "%s" if self.backend == "postgresql" else "?"
                    ),
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
            row = self._fetchone(
                conn,
                "SELECT approval_id, run_id, step_id, tenant_id, status, created_at, updated_at, decision, approver_id, comments, metadata FROM workflow_approvals WHERE approval_id = {p}".replace(
                    "{p}", "%s" if self.backend == "postgresql" else "?"
                ),
                (approval_id,),
            )
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
        params: list[Any] = [tenant_id]
        query = "SELECT approval_id, run_id, step_id, tenant_id, status, created_at, updated_at, decision, approver_id, comments, metadata FROM workflow_approvals WHERE tenant_id = {p}".replace(
            "{p}", "%s" if self.backend == "postgresql" else "?"
        )
        if status:
            query += " AND status = " + ("%s" if self.backend == "postgresql" else "?")
            params.append(status)
        query += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = self._fetchall(conn, query, tuple(params))
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
            row = self._fetchone(
                conn,
                "SELECT approval_id, run_id, step_id, tenant_id, status, created_at, updated_at, decision, approver_id, comments, metadata FROM workflow_approvals WHERE run_id = {p} AND step_id = {p}".replace(
                    "{p}", "%s" if self.backend == "postgresql" else "?"
                ),
                (run_id, step_id),
            )
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
        now = _now()
        journal_id = f"journal_{run_id}_{phase}_{status}_{attempt}_{now}"
        payload = details or {}
        with self._transaction() as conn:
            self._execute(
                conn,
                "INSERT INTO workflow_state_journal (journal_id, run_id, step_id, phase, status, attempt, details, created_at) VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})".replace(
                    "{p}", "%s" if self.backend == "postgresql" else "?"
                ),
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
        params: list[Any] = [run_id]
        query = "SELECT journal_id, run_id, step_id, phase, status, attempt, details, created_at FROM workflow_state_journal WHERE run_id = {p}".replace(
            "{p}", "%s" if self.backend == "postgresql" else "?"
        )
        if phase:
            query += " AND phase = " + ("%s" if self.backend == "postgresql" else "?")
            params.append(phase)
        if step_id:
            query += " AND step_id = " + ("%s" if self.backend == "postgresql" else "?")
            params.append(step_id)
        query += " ORDER BY created_at ASC"
        with self._connect() as conn:
            rows = self._fetchall(conn, query, tuple(params))
        return [
            WorkflowJournalEntry(
                journal_id=r[0],
                run_id=r[1],
                step_id=r[2],
                phase=r[3],
                status=r[4],
                attempt=r[5],
                details=json.loads(r[6]),
                created_at=r[7],
            )
            for r in rows
        ]

    def backup(self, backup_path: Path) -> Path:
        if self.backend != "sqlite":
            raise NotImplementedError("Use managed SQL snapshots for PostgreSQL backups")
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.db_path, backup_path)
        return backup_path

    def restore(self, backup_path: Path) -> None:
        if self.backend != "sqlite":
            raise NotImplementedError("Use managed SQL restore workflows for PostgreSQL")
        shutil.copy2(backup_path, self.db_path)
        self._ensure_schema()

    def apply_retention(self, *, keep_days: int = 30) -> dict[str, int]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).isoformat()
        with self._transaction() as conn:
            if self.backend == "sqlite":
                events_deleted = conn.execute(
                    "DELETE FROM workflow_events WHERE created_at < ?", (cutoff,)
                ).rowcount
                journal_deleted = conn.execute(
                    "DELETE FROM workflow_state_journal WHERE created_at < ?", (cutoff,)
                ).rowcount
            else:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM workflow_events WHERE created_at < %s", (cutoff,))
                    events_deleted = cur.rowcount
                    cur.execute(
                        "DELETE FROM workflow_state_journal WHERE created_at < %s", (cutoff,)
                    )
                    journal_deleted = cur.rowcount
        return {"workflow_events": events_deleted, "workflow_state_journal": journal_deleted}
