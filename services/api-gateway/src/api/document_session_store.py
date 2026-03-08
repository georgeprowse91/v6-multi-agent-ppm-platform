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
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[assignment]


@dataclass(frozen=True)
class DocumentSessionStorageSelection:
    db_path: Path
    backend: str
    durability_mode: str
    source: str
    connection_url: str | None = None


@runtime_checkable
class DocumentSessionRepository(Protocol):
    def create_session(self, payload: dict[str, Any]) -> None: ...

    def get_session(self, session_id: str) -> dict[str, Any] | None: ...

    def update_session(self, session_id: str, **changes: Any) -> dict[str, Any] | None: ...


@runtime_checkable
class DocumentVersionRepository(Protocol):
    def record_version(
        self,
        document_id: str,
        version: int,
        content: str,
        persisted_at: str,
        persisted_by: str,
        *,
        summary: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...


def resolve_document_session_storage(
    *,
    environment: str,
    configured_db_path: str | None = None,
) -> DocumentSessionStorageSelection:
    from common.env_validation import (
        durability_mode_for_storage,
        enforce_no_default_file_backed_storage,
    )

    connection_url = os.getenv("DOCUMENT_SESSION_DB_URL")
    if connection_url:
        return DocumentSessionStorageSelection(
            db_path=Path(":memory:"),
            backend="postgresql",
            durability_mode="network",
            source="explicit",
            connection_url=connection_url,
        )

    default_path = "data/documents/sessions.db"
    selected = configured_db_path or os.getenv("DOCUMENT_SESSION_DB_PATH") or default_path
    used_default = not (configured_db_path or os.getenv("DOCUMENT_SESSION_DB_PATH"))
    enforce_no_default_file_backed_storage(
        service_name="api-gateway document session store",
        setting_names=("DOCUMENT_SESSION_DB_PATH", "DOCUMENT_SESSION_DB_URL"),
        selected_value=selected,
        used_default=used_default,
        environment=environment,
        remediation_hint=(
            "Provide DOCUMENT_SESSION_DB_PATH on persistent storage (for example a mounted "
            "volume path) or DOCUMENT_SESSION_DB_URL for managed SQL."
        ),
    )
    return DocumentSessionStorageSelection(
        db_path=Path(selected),
        backend="sqlite",
        durability_mode=durability_mode_for_storage(selected),
        source="default" if used_default else "explicit",
    )


class DocumentSessionStore:
    def __init__(self, db_path: Path | None = None, *, connection_url: str | None = None) -> None:
        self._db_path = db_path or Path(":memory:")
        self._connection_url = connection_url
        self._backend = "postgresql" if connection_url else "sqlite"
        if self._backend == "sqlite":
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @classmethod
    def from_selection(cls, selection: DocumentSessionStorageSelection) -> DocumentSessionStore:
        return cls(db_path=selection.db_path, connection_url=selection.connection_url)

    def _connect(self) -> Any:
        if self._backend == "sqlite":
            conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            return conn
        if psycopg2 is None:
            raise RuntimeError("psycopg2 is required for PostgreSQL document session storage")
        return psycopg2.connect(self._connection_url)

    @contextmanager
    def _transaction(self) -> Iterator[Any]:
        conn = self._connect()
        try:
            if self._backend == "sqlite":
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

    def _initialize(self) -> None:
        migration = (
            Path(__file__).resolve().parents[2]
            / "migrations"
            / "sql"
            / f"001_init_{self._backend}.sql"
        )
        sql = migration.read_text(encoding="utf-8")
        with self._connect() as conn:
            if self._backend == "sqlite":
                conn.executescript(sql)
            else:
                with conn.cursor() as cur:
                    cur.execute(sql)
            conn.commit()

    def close(self) -> None:
        return None

    def create_session(self, payload: dict[str, Any]) -> None:
        with self._transaction() as conn:
            if self._backend == "sqlite":
                conn.execute(
                    """
                    INSERT INTO document_sessions (
                        session_id, document_id, tenant_id, status, started_by, started_at,
                        updated_at, collaborators_json, content, version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload["session_id"],
                        payload["document_id"],
                        payload["tenant_id"],
                        payload["status"],
                        payload["started_by"],
                        payload["started_at"],
                        payload["updated_at"],
                        json.dumps(payload.get("collaborators", [])),
                        payload.get("content", ""),
                        payload.get("version", 1),
                    ),
                )
            else:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO document_sessions (
                            session_id, document_id, tenant_id, status, started_by, started_at,
                            updated_at, collaborators_json, content, version
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                        """,
                        (
                            payload["session_id"],
                            payload["document_id"],
                            payload["tenant_id"],
                            payload["status"],
                            payload["started_by"],
                            payload["started_at"],
                            payload["updated_at"],
                            json.dumps(payload.get("collaborators", [])),
                            payload.get("content", ""),
                            payload.get("version", 1),
                        ),
                    )

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            if self._backend == "sqlite":
                row = conn.execute(
                    "SELECT * FROM document_sessions WHERE session_id = ?", (session_id,)
                ).fetchone()
                if row is None:
                    return None
                data = dict(row)
            else:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM document_sessions WHERE session_id = %s", (session_id,)
                    )
                    row = cur.fetchone()
                    if row is None:
                        return None
                    cols = [desc[0] for desc in cur.description]
                    data = dict(zip(cols, row))
        return {
            "session_id": data["session_id"],
            "document_id": data["document_id"],
            "tenant_id": data["tenant_id"],
            "status": data["status"],
            "started_by": data["started_by"],
            "started_at": data["started_at"],
            "updated_at": data["updated_at"],
            "collaborators": (
                json.loads(data["collaborators_json"])
                if isinstance(data["collaborators_json"], str)
                else data["collaborators_json"]
            ),
            "content": data["content"],
            "version": data["version"],
        }

    def update_session(self, session_id: str, **changes: Any) -> dict[str, Any] | None:
        with self._transaction() as conn:
            if self._backend == "sqlite":
                row = conn.execute(
                    "SELECT * FROM document_sessions WHERE session_id = ?", (session_id,)
                ).fetchone()
                if row is None:
                    return None
                existing = dict(row)
            else:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM document_sessions WHERE session_id = %s FOR UPDATE",
                        (session_id,),
                    )
                    row = cur.fetchone()
                    if row is None:
                        return None
                    cols = [desc[0] for desc in cur.description]
                    existing = dict(zip(cols, row))
            merged = {
                "session_id": session_id,
                "document_id": existing["document_id"],
                "tenant_id": existing["tenant_id"],
                "status": existing["status"],
                "started_by": existing["started_by"],
                "started_at": existing["started_at"],
                "updated_at": existing["updated_at"],
                "collaborators": (
                    json.loads(existing["collaborators_json"])
                    if isinstance(existing["collaborators_json"], str)
                    else existing["collaborators_json"]
                ),
                "content": existing["content"],
                "version": existing["version"],
            }
            merged.update(changes)
            if self._backend == "sqlite":
                conn.execute(
                    """
                    UPDATE document_sessions
                    SET document_id = ?, tenant_id = ?, status = ?, started_by = ?, started_at = ?,
                        updated_at = ?, collaborators_json = ?, content = ?, version = ?
                    WHERE session_id = ?
                    """,
                    (
                        merged["document_id"],
                        merged["tenant_id"],
                        merged["status"],
                        merged["started_by"],
                        merged["started_at"],
                        merged["updated_at"],
                        json.dumps(merged["collaborators"]),
                        merged["content"],
                        merged["version"],
                        session_id,
                    ),
                )
            else:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE document_sessions
                        SET document_id = %s, tenant_id = %s, status = %s, started_by = %s, started_at = %s,
                            updated_at = %s, collaborators_json = %s::jsonb, content = %s, version = %s
                        WHERE session_id = %s
                        """,
                        (
                            merged["document_id"],
                            merged["tenant_id"],
                            merged["status"],
                            merged["started_by"],
                            merged["started_at"],
                            merged["updated_at"],
                            json.dumps(merged["collaborators"]),
                            merged["content"],
                            merged["version"],
                            session_id,
                        ),
                    )
        return merged

    def record_version(
        self,
        document_id: str,
        version: int,
        content: str,
        persisted_at: str,
        persisted_by: str,
        *,
        summary: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._transaction() as conn:
            if self._backend == "sqlite":
                conn.execute(
                    """
                    INSERT OR IGNORE INTO document_versions (
                        document_id, version, content, persisted_at, persisted_by, summary, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        version,
                        content,
                        persisted_at,
                        persisted_by,
                        summary,
                        json.dumps(metadata or {}),
                    ),
                )
            else:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO document_versions (
                            document_id, version, content, persisted_at, persisted_by, summary, metadata_json
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (document_id, version) DO NOTHING
                        """,
                        (
                            document_id,
                            version,
                            content,
                            persisted_at,
                            persisted_by,
                            summary,
                            json.dumps(metadata or {}),
                        ),
                    )

    def backup(self, backup_path: Path) -> Path:
        if self._backend != "sqlite":
            raise NotImplementedError("Use managed SQL snapshots for PostgreSQL backups")
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self._db_path, backup_path)
        return backup_path

    def restore(self, backup_path: Path) -> None:
        if self._backend != "sqlite":
            raise NotImplementedError("Use managed SQL restore workflows for PostgreSQL")
        shutil.copy2(backup_path, self._db_path)
        self._initialize()

    def apply_retention(self, *, keep_days: int = 30) -> dict[str, int]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).isoformat()
        with self._transaction() as conn:
            if self._backend == "sqlite":
                deleted = conn.execute(
                    "DELETE FROM document_versions WHERE persisted_at < ?", (cutoff,)
                ).rowcount
            else:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM document_versions WHERE persisted_at < %s", (cutoff,))
                    deleted = cur.rowcount
        return {"document_versions": deleted}
