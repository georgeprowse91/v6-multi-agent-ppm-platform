from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from security.crypto import decrypt_text, encrypt_text

ENCRYPTION_PREFIX = "enc:"


@dataclass
class DocumentRecord:
    document_id: str
    tenant_id: str
    name: str
    classification: str
    retention_days: int
    content: str
    created_at: datetime
    retention_until: datetime
    metadata: dict[str, Any]


class DocumentStore:
    def __init__(self, db_path: Path, encryption_key: str) -> None:
        self.db_path = db_path
        self._encryption_key = encryption_key
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            if str(self.db_path) == ":memory:":
                raise ValueError("in-memory document store is not allowed in production")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    retention_days INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    retention_until TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
                """
            )

    def _decrypt_content(self, content: str) -> str:
        if content.startswith(ENCRYPTION_PREFIX):
            token = content[len(ENCRYPTION_PREFIX) :]
            return decrypt_text(token, key=self._encryption_key)
        environment = os.getenv("ENVIRONMENT", "development").lower()
        if environment == "production":
            raise ValueError("unencrypted document content detected in production")
        return content

    def _encrypt_content(self, content: str) -> str:
        token = encrypt_text(content, key=self._encryption_key)
        return f"{ENCRYPTION_PREFIX}{token}"

    def _serialize(self, row: sqlite3.Row) -> DocumentRecord:
        return DocumentRecord(
            document_id=row["document_id"],
            tenant_id=row["tenant_id"],
            name=row["name"],
            classification=row["classification"],
            retention_days=row["retention_days"],
            content=self._decrypt_content(row["content"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            retention_until=datetime.fromisoformat(row["retention_until"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def create_document(
        self,
        tenant_id: str,
        name: str,
        classification: str,
        retention_days: int,
        content: str,
        metadata: dict[str, Any],
    ) -> DocumentRecord:
        now = datetime.now(timezone.utc)
        retention_until = now + timedelta(days=retention_days)
        document_id = str(uuid4())
        encrypted_content = self._encrypt_content(content)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO documents
                    (document_id, tenant_id, name, classification, retention_days, content, created_at, retention_until, metadata)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    tenant_id,
                    name,
                    classification,
                    retention_days,
                    encrypted_content,
                    now.isoformat(),
                    retention_until.isoformat(),
                    json.dumps(metadata),
                ),
            )
        return DocumentRecord(
            document_id=document_id,
            tenant_id=tenant_id,
            name=name,
            classification=classification,
            retention_days=retention_days,
            content=content,
            created_at=now,
            retention_until=retention_until,
            metadata=metadata,
        )

    def list_documents(self, tenant_id: str, *, limit: int, offset: int) -> list[DocumentRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM documents WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (tenant_id, limit, offset),
            ).fetchall()
        return [self._serialize(row) for row in rows]

    def count_documents(self, tenant_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM documents WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchone()
        return int(row["count"]) if row else 0

    def ping(self) -> None:
        with self._connect() as conn:
            conn.execute("SELECT 1")

    def get_document(self, tenant_id: str, document_id: str) -> DocumentRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE tenant_id = ? AND document_id = ?",
                (tenant_id, document_id),
            ).fetchone()
        return self._serialize(row) if row else None
