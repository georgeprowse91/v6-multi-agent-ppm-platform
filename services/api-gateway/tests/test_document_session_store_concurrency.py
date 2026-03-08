from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from api.document_session_store import DocumentSessionStore


def _count_versions(db_path: Path, document_id: str, version: int) -> int:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM document_versions WHERE document_id = ? AND version = ?",
            (document_id, version),
        ).fetchone()
        return int(row[0])
    finally:
        conn.close()


def test_version_write_is_idempotent_under_parallel_requests(tmp_path: Path) -> None:
    db_path = tmp_path / "sessions.db"
    store = DocumentSessionStore(db_path)
    store.create_session(
        {
            "session_id": "s1",
            "document_id": "doc-1",
            "tenant_id": "tenant-1",
            "status": "active",
            "started_by": "u1",
            "started_at": "2025-01-01T00:00:00+00:00",
            "updated_at": "2025-01-01T00:00:00+00:00",
            "collaborators": [],
            "content": "a",
            "version": 1,
        }
    )

    def write(_: int) -> None:
        store.record_version(
            document_id="doc-1",
            version=1,
            content="hello",
            persisted_at="2025-01-01T00:00:01+00:00",
            persisted_by="u1",
            metadata={"request": "same"},
        )

    with ThreadPoolExecutor(max_workers=10) as executor:
        list(executor.map(write, range(60)))

    assert _count_versions(db_path, "doc-1", 1) == 1


def test_backup_restore_and_retention_hooks(tmp_path: Path) -> None:
    db_path = tmp_path / "sessions.db"
    store = DocumentSessionStore(db_path)
    store.record_version(
        document_id="doc-2",
        version=1,
        content="old",
        persisted_at="2000-01-01T00:00:00+00:00",
        persisted_by="u1",
    )
    backup = store.backup(tmp_path / "backup" / "sessions.db")
    retained = store.apply_retention(keep_days=1)
    assert retained["document_versions"] >= 1

    store.restore(backup)
    assert _count_versions(db_path, "doc-2", 1) == 1
