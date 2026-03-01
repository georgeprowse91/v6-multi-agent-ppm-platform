from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class KnowledgeDatabase:
    """SQLite-backed knowledge database for documents, metadata, and graph relationships."""

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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    doc_type TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    author TEXT,
                    owner TEXT,
                    status TEXT NOT NULL,
                    source TEXT,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    modified_at TEXT NOT NULL
                )
                """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_versions (
                    version_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_tags (
                    document_id TEXT NOT NULL,
                    tag TEXT NOT NULL
                )
                """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    node_id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    attributes TEXT NOT NULL
                )
                """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS graph_edges (
                    edge_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_interactions (
                    interaction_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    interaction_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_tenant ON documents(tenant_id)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_versions_document ON document_versions(document_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tags_document ON document_tags(document_id)"
            )

    def upsert_document(self, document: dict[str, Any]) -> None:
        metadata = json.dumps(document.get("metadata", {}))
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT document_id FROM documents WHERE document_id = ?",
                (document["document_id"],),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE documents
                    SET title = ?, content = ?, doc_type = ?, classification = ?, author = ?, owner = ?,
                        status = ?, source = ?, metadata = ?, modified_at = ?
                    WHERE document_id = ?
                    """,
                    (
                        document.get("title"),
                        document.get("content", ""),
                        document.get("type") or document.get("doc_type") or "report",
                        document.get("classification", "internal"),
                        document.get("author"),
                        document.get("owner"),
                        document.get("status", "draft"),
                        document.get("source"),
                        metadata,
                        document.get("modified_at") or now,
                        document["document_id"],
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO documents
                        (document_id, tenant_id, title, content, doc_type, classification, author, owner,
                         status, source, metadata, created_at, modified_at)
                    VALUES
                        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document["document_id"],
                        document.get("tenant_id", "default"),
                        document.get("title"),
                        document.get("content", ""),
                        document.get("type") or document.get("doc_type") or "report",
                        document.get("classification", "internal"),
                        document.get("author"),
                        document.get("owner"),
                        document.get("status", "draft"),
                        document.get("source"),
                        metadata,
                        document.get("created_at") or now,
                        document.get("modified_at") or now,
                    ),
                )

            conn.execute(
                "DELETE FROM document_tags WHERE document_id = ?", (document["document_id"],)
            )
            for tag in document.get("tags", []):
                conn.execute(
                    "INSERT INTO document_tags (document_id, tag) VALUES (?, ?)",
                    (document["document_id"], tag),
                )

    def record_version(self, document: dict[str, Any]) -> None:
        version_id = str(uuid4())
        created_at = document.get("modified_at") or datetime.now(timezone.utc).isoformat()
        metadata = json.dumps(document.get("metadata", {}))
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO document_versions
                    (version_id, document_id, version_number, content, metadata, created_at)
                VALUES
                    (?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    document["document_id"],
                    document.get("version", 1),
                    document.get("content", ""),
                    metadata,
                    created_at,
                ),
            )

    def record_interaction(
        self, document_id: str, interaction_type: str, payload: dict[str, Any]
    ) -> None:
        interaction_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO document_interactions
                    (interaction_id, document_id, interaction_type, payload, created_at)
                VALUES
                    (?, ?, ?, ?, ?)
                """,
                (interaction_id, document_id, interaction_type, json.dumps(payload), created_at),
            )

    def list_interactions(self, document_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM document_interactions WHERE document_id = ? ORDER BY created_at",
                (document_id,),
            ).fetchall()
        interactions = []
        for row in rows:
            interactions.append(
                {
                    "interaction_id": row["interaction_id"],
                    "document_id": row["document_id"],
                    "interaction_type": row["interaction_type"],
                    "payload": json.loads(row["payload"]),
                    "created_at": row["created_at"],
                }
            )
        return interactions

    def upsert_graph(self, nodes: dict[str, dict[str, Any]], edges: list[dict[str, Any]]) -> None:
        with self._connect() as conn:
            for node_id, node in nodes.items():
                conn.execute(
                    """
                    INSERT INTO graph_nodes (node_id, node_type, attributes)
                    VALUES (?, ?, ?)
                    ON CONFLICT(node_id) DO UPDATE SET
                        node_type = excluded.node_type,
                        attributes = excluded.attributes
                    """,
                    (node_id, node.get("type"), json.dumps(node.get("attributes", {}))),
                )
            for edge in edges:
                conn.execute(
                    """
                    INSERT INTO graph_edges (edge_id, source_id, target_id, relation, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        edge.get("from"),
                        edge.get("to"),
                        edge.get("relation"),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

    def list_documents(self, tenant_id: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if tenant_id:
                rows = conn.execute(
                    "SELECT * FROM documents WHERE tenant_id = ?",
                    (tenant_id,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM documents").fetchall()
        documents = []
        for row in rows:
            documents.append(
                {
                    "document_id": row["document_id"],
                    "tenant_id": row["tenant_id"],
                    "title": row["title"],
                    "content": row["content"],
                    "type": row["doc_type"],
                    "classification": row["classification"],
                    "author": row["author"],
                    "owner": row["owner"],
                    "status": row["status"],
                    "source": row["source"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "created_at": row["created_at"],
                    "modified_at": row["modified_at"],
                }
            )
        return documents
