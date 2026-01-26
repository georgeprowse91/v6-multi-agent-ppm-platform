from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


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
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
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

    def _serialize(self, row: sqlite3.Row) -> DocumentRecord:
        return DocumentRecord(
            document_id=row["document_id"],
            tenant_id=row["tenant_id"],
            name=row["name"],
            classification=row["classification"],
            retention_days=row["retention_days"],
            content=row["content"],
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
                    content,
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

    def list_documents(self, tenant_id: str) -> list[DocumentRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM documents WHERE tenant_id = ? ORDER BY created_at DESC",
                (tenant_id,),
            ).fetchall()
        return [self._serialize(row) for row in rows]

    def get_document(self, tenant_id: str, document_id: str) -> DocumentRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE tenant_id = ? AND document_id = ?",
                (tenant_id, document_id),
            ).fetchone()
        return self._serialize(row) if row else None
