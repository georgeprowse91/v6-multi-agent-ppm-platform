from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


class MemoryService:
    """Unified key-value memory service with optional SQLite persistence and TTL."""

    def __init__(
        self,
        *,
        backend: str = "memory",
        sqlite_path: str | None = None,
        default_ttl_seconds: int | None = None,
    ) -> None:
        self._backend = backend
        self._default_ttl_seconds = default_ttl_seconds
        self._lock = threading.RLock()
        self._memory_store: dict[str, tuple[dict[str, Any], float | None]] = {}
        self._conn: sqlite3.Connection | None = None

        if backend == "sqlite":
            if not sqlite_path:
                sqlite_path = str(Path(".runtime") / "memory_service.db")
            path = Path(sqlite_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(path, check_same_thread=False)
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_context (
                    memory_key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    expires_at REAL
                )
                """
            )
            self._conn.commit()
        elif backend != "memory":
            raise ValueError("backend must be 'memory' or 'sqlite'")

    def save_context(self, key: str, data: dict[str, Any]) -> None:
        expires_at = (
            time.time() + self._default_ttl_seconds
            if self._default_ttl_seconds is not None
            else None
        )
        with self._lock:
            if self._backend == "memory":
                self._memory_store[key] = (dict(data), expires_at)
                return

            assert self._conn is not None
            self._conn.execute(
                """
                INSERT INTO memory_context(memory_key, data, expires_at)
                VALUES (?, ?, ?)
                ON CONFLICT(memory_key)
                DO UPDATE SET data=excluded.data, expires_at=excluded.expires_at
                """,
                (key, json.dumps(data), expires_at),
            )
            self._conn.commit()

    def load_context(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            if self._backend == "memory":
                item = self._memory_store.get(key)
                if item is None:
                    return None
                data, expires_at = item
                if self._is_expired(expires_at):
                    self._memory_store.pop(key, None)
                    return None
                return dict(data)

            assert self._conn is not None
            row = self._conn.execute(
                "SELECT data, expires_at FROM memory_context WHERE memory_key = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None
            payload, expires_at = row
            if self._is_expired(expires_at):
                self.delete_context(key)
                return None
            return json.loads(payload)

    def delete_context(self, key: str) -> None:
        with self._lock:
            if self._backend == "memory":
                self._memory_store.pop(key, None)
                return

            assert self._conn is not None
            self._conn.execute("DELETE FROM memory_context WHERE memory_key = ?", (key,))
            self._conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @staticmethod
    def _is_expired(expires_at: float | None) -> bool:
        return expires_at is not None and expires_at <= time.time()
