from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any




@dataclass(frozen=True)
class DocumentSessionStorageSelection:
    db_path: Path
    backend: str
    durability_mode: str
    source: str


def resolve_document_session_storage(
    *,
    environment: str,
    configured_db_path: str | None = None,
) -> DocumentSessionStorageSelection:
    from common.env_validation import (
        durability_mode_for_storage,
        enforce_no_default_file_backed_storage,
    )

    default_path = "data/documents/sessions.db"
    selected = configured_db_path or os.getenv("DOCUMENT_SESSION_DB_PATH") or default_path
    used_default = not (configured_db_path or os.getenv("DOCUMENT_SESSION_DB_PATH"))
    enforce_no_default_file_backed_storage(
        service_name="api-gateway document session store",
        setting_names=("DOCUMENT_SESSION_DB_PATH",),
        selected_value=selected,
        used_default=used_default,
        environment=environment,
        remediation_hint=(
            "Provide DOCUMENT_SESSION_DB_PATH on persistent storage (for example a mounted "
            "volume path) to prevent session/version data loss on restart."
        ),
    )
    return DocumentSessionStorageSelection(
        db_path=Path(selected),
        backend="sqlite",
        durability_mode=durability_mode_for_storage(selected),
        source="default" if used_default else "explicit",
    )
class DocumentSessionStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS document_sessions (
                session_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                status TEXT NOT NULL,
                started_by TEXT NOT NULL,
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                collaborators_json TEXT NOT NULL,
                content TEXT NOT NULL,
                version INTEGER NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS document_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                content TEXT NOT NULL,
                persisted_at TEXT NOT NULL,
                persisted_by TEXT NOT NULL,
                summary TEXT,
                metadata_json TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def create_session(self, payload: dict[str, Any]) -> None:
        self._conn.execute(
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
        self._conn.commit()

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM document_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "session_id": row["session_id"],
            "document_id": row["document_id"],
            "tenant_id": row["tenant_id"],
            "status": row["status"],
            "started_by": row["started_by"],
            "started_at": row["started_at"],
            "updated_at": row["updated_at"],
            "collaborators": json.loads(row["collaborators_json"]),
            "content": row["content"],
            "version": row["version"],
        }

    def update_session(self, session_id: str, **changes: Any) -> dict[str, Any] | None:
        existing = self.get_session(session_id)
        if existing is None:
            return None
        merged = {**existing, **changes}
        self._conn.execute(
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
        self._conn.commit()
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
        self._conn.execute(
            """
            INSERT INTO document_versions (
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
        self._conn.commit()
