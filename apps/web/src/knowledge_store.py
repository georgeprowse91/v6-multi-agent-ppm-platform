from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

_SAFE_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,127}$")


def _quote_identifier(name: str) -> str:
    """Validate and double-quote a SQLite identifier to prevent SQL injection."""
    if not _SAFE_IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return f'"{name}"'


@dataclass
class DocumentSummaryRecord:
    document_id: str
    document_key: str
    project_id: str
    name: str
    doc_type: str
    classification: str
    latest_version: int
    latest_status: str
    created_at: datetime
    updated_at: datetime


@dataclass
class DocumentSearchRecord(DocumentSummaryRecord):
    content: str


@dataclass
class DocumentVersionRecord:
    document_id: str
    document_key: str
    project_id: str
    name: str
    doc_type: str
    classification: str
    version: int
    status: str
    content: str
    created_at: datetime
    metadata: dict[str, Any]


@dataclass
class LessonRecord:
    lesson_id: str
    project_id: str
    stage_id: str | None
    stage_name: str | None
    title: str
    description: str
    tags: list[str]
    topics: list[str]
    created_at: datetime
    updated_at: datetime


class KnowledgeStore:
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
                    document_key TEXT NOT NULL UNIQUE,
                    project_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    doc_type TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_versions (
                    version_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
                """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lessons (
                    lesson_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    stage_id TEXT,
                    stage_name TEXT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    topics TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_versions_document ON document_versions(document_id)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lessons_project ON lessons(project_id)")
            self._ensure_column(conn, "documents", "edit_history", "TEXT", default_value="[]")

    def _ensure_column(
        self,
        conn: sqlite3.Connection,
        table: str,
        column: str,
        column_type: str,
        *,
        default_value: str | None = None,
    ) -> None:
        safe_table = _quote_identifier(table)
        safe_column = _quote_identifier(column)
        if not _SAFE_IDENTIFIER_RE.match(column_type):
            raise ValueError(f"Invalid SQL column type: {column_type!r}")
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({safe_table})")}
        if column in columns:
            return
        conn.execute(f"ALTER TABLE {safe_table} ADD COLUMN {safe_column} {column_type}")
        if default_value is not None:
            conn.execute(
                f"UPDATE {safe_table} SET {safe_column} = ? WHERE {safe_column} IS NULL",
                (default_value,),
            )

    def _extract_edit_history(self, row: sqlite3.Row | None) -> list[dict[str, Any]]:
        if not row:
            return []
        history = row["edit_history"] if "edit_history" in row.keys() else None
        if not history:
            return []
        try:
            return json.loads(history)
        except json.JSONDecodeError:
            return []

    def _serialize_document_summary(self, row: sqlite3.Row) -> DocumentSummaryRecord:
        return DocumentSummaryRecord(
            document_id=row["document_id"],
            document_key=row["document_key"],
            project_id=row["project_id"],
            name=row["name"],
            doc_type=row["doc_type"],
            classification=row["classification"],
            latest_version=row["latest_version"],
            latest_status=row["latest_status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _serialize_document_search(self, row: sqlite3.Row) -> DocumentSearchRecord:
        return DocumentSearchRecord(
            document_id=row["document_id"],
            document_key=row["document_key"],
            project_id=row["project_id"],
            name=row["name"],
            doc_type=row["doc_type"],
            classification=row["classification"],
            latest_version=row["latest_version"],
            latest_status=row["latest_status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            content=row["content"],
        )

    def _serialize_version(self, row: sqlite3.Row) -> DocumentVersionRecord:
        return DocumentVersionRecord(
            document_id=row["document_id"],
            document_key=row["document_key"],
            project_id=row["project_id"],
            name=row["name"],
            doc_type=row["doc_type"],
            classification=row["classification"],
            version=row["version_number"],
            status=row["status"],
            content=row["content"],
            created_at=datetime.fromisoformat(row["created_at"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def _serialize_lesson(self, row: sqlite3.Row) -> LessonRecord:
        return LessonRecord(
            lesson_id=row["lesson_id"],
            project_id=row["project_id"],
            stage_id=row["stage_id"],
            stage_name=row["stage_name"],
            title=row["title"],
            description=row["description"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            topics=json.loads(row["topics"]) if row["topics"] else [],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def create_document_version(
        self,
        project_id: str,
        document_key: str,
        name: str,
        doc_type: str,
        classification: str,
        status: str,
        content: str,
        metadata: dict[str, Any],
        *,
        track_edits: bool = False,
    ) -> DocumentVersionRecord:
        now = datetime.now(timezone.utc)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE document_key = ?",
                (document_key,),
            ).fetchone()
            edit_history = self._extract_edit_history(row)
            if row:
                document_id = row["document_id"]
                conn.execute(
                    """
                    UPDATE documents
                    SET name = ?, doc_type = ?, classification = ?, project_id = ?, updated_at = ?
                    WHERE document_id = ?
                    """,
                    (
                        name,
                        doc_type,
                        classification,
                        project_id,
                        now.isoformat(),
                        document_id,
                    ),
                )
            else:
                document_id = str(uuid4())
                conn.execute(
                    """
                    INSERT INTO documents
                        (document_id, document_key, project_id, name, doc_type, classification, created_at, updated_at, edit_history)
                    VALUES
                        (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        document_key,
                        project_id,
                        name,
                        doc_type,
                        classification,
                        now.isoformat(),
                        now.isoformat(),
                        json.dumps(edit_history),
                    ),
                )

            current_version = conn.execute(
                "SELECT MAX(version_number) AS latest FROM document_versions WHERE document_id = ?",
                (document_id,),
            ).fetchone()["latest"]
            version_number = int(current_version or 0) + 1
            version_id = str(uuid4())
            version_metadata = dict(metadata)
            if track_edits:
                edit_entry = {
                    "version": version_number,
                    "status": status,
                    "editedAt": now.isoformat(),
                    "editedBy": metadata.get("editedBy")
                    or metadata.get("updatedBy")
                    or metadata.get("createdBy")
                    or "unknown",
                    "source": metadata.get("source") or "document_canvas",
                    "provenance": metadata.get("provenance"),
                }
                edit_history.append(edit_entry)
                conn.execute(
                    "UPDATE documents SET edit_history = ? WHERE document_id = ?",
                    (json.dumps(edit_history), document_id),
                )
                version_metadata["editHistory"] = edit_history
            conn.execute(
                """
                INSERT INTO document_versions
                    (version_id, document_id, version_number, status, content, created_at, metadata)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    document_id,
                    version_number,
                    status,
                    content,
                    now.isoformat(),
                    json.dumps(version_metadata),
                ),
            )

        return DocumentVersionRecord(
            document_id=document_id,
            document_key=document_key,
            project_id=project_id,
            name=name,
            doc_type=doc_type,
            classification=classification,
            version=version_number,
            status=status,
            content=content,
            created_at=now,
            metadata=version_metadata,
        )

    def list_documents(
        self, project_id: str | None = None, query: str | None = None
    ) -> list[DocumentSummaryRecord]:
        filters: list[str] = []
        params: list[Any] = []
        if project_id:
            filters.append("documents.project_id = ?")
            params.append(project_id)
        if query:
            filters.append("(documents.name LIKE ? OR latest_versions.content LIKE ?)")
            like = f"%{query}%"
            params.extend([like, like])

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        sql = f"""
            SELECT
                documents.document_id,
                documents.document_key,
                documents.project_id,
                documents.name,
                documents.doc_type,
                documents.classification,
                documents.created_at,
                documents.updated_at,
                latest_versions.version_number AS latest_version,
                latest_versions.status AS latest_status
            FROM documents
            JOIN (
                SELECT document_id, version_number, status, content
                FROM document_versions
                WHERE (document_id, version_number) IN (
                    SELECT document_id, MAX(version_number)
                    FROM document_versions
                    GROUP BY document_id
                )
            ) AS latest_versions
            ON documents.document_id = latest_versions.document_id
            {where_clause}
            ORDER BY documents.updated_at DESC
        """

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._serialize_document_summary(row) for row in rows]

    def search_documents(
        self, query: str | None = None, project_ids: list[str] | None = None
    ) -> list[DocumentSearchRecord]:
        filters: list[str] = []
        params: list[Any] = []
        if project_ids:
            placeholders = ", ".join(["?"] * len(project_ids))
            filters.append(f"documents.project_id IN ({placeholders})")
            params.extend(project_ids)
        if query:
            filters.append("(documents.name LIKE ? OR latest_versions.content LIKE ?)")
            like = f"%{query}%"
            params.extend([like, like])

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        sql = f"""
            SELECT
                documents.document_id,
                documents.document_key,
                documents.project_id,
                documents.name,
                documents.doc_type,
                documents.classification,
                documents.created_at,
                documents.updated_at,
                latest_versions.version_number AS latest_version,
                latest_versions.status AS latest_status,
                latest_versions.content AS content
            FROM documents
            JOIN (
                SELECT document_id, version_number, status, content
                FROM document_versions
                WHERE (document_id, version_number) IN (
                    SELECT document_id, MAX(version_number)
                    FROM document_versions
                    GROUP BY document_id
                )
            ) AS latest_versions
            ON documents.document_id = latest_versions.document_id
            {where_clause}
            ORDER BY documents.updated_at DESC
        """

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._serialize_document_search(row) for row in rows]

    def list_versions(self, document_id: str) -> list[DocumentVersionRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    documents.document_id,
                    documents.document_key,
                    documents.project_id,
                    documents.name,
                    documents.doc_type,
                    documents.classification,
                    document_versions.version_number,
                    document_versions.status,
                    document_versions.content,
                    document_versions.created_at,
                    document_versions.metadata
                FROM document_versions
                JOIN documents ON documents.document_id = document_versions.document_id
                WHERE document_versions.document_id = ?
                ORDER BY document_versions.version_number DESC
                """,
                (document_id,),
            ).fetchall()
        return [self._serialize_version(row) for row in rows]

    def create_lesson(
        self,
        project_id: str,
        stage_id: str | None,
        stage_name: str | None,
        title: str,
        description: str,
        tags: list[str],
        topics: list[str],
    ) -> LessonRecord:
        now = datetime.now(timezone.utc)
        lesson_id = str(uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO lessons
                    (lesson_id, project_id, stage_id, stage_name, title, description, tags, topics, created_at, updated_at)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lesson_id,
                    project_id,
                    stage_id,
                    stage_name,
                    title,
                    description,
                    json.dumps(tags),
                    json.dumps(topics),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
        return LessonRecord(
            lesson_id=lesson_id,
            project_id=project_id,
            stage_id=stage_id,
            stage_name=stage_name,
            title=title,
            description=description,
            tags=tags,
            topics=topics,
            created_at=now,
            updated_at=now,
        )

    def update_lesson(
        self,
        lesson_id: str,
        title: str,
        description: str,
        tags: list[str],
        topics: list[str],
        stage_id: str | None,
        stage_name: str | None,
    ) -> LessonRecord | None:
        now = datetime.now(timezone.utc)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM lessons WHERE lesson_id = ?",
                (lesson_id,),
            ).fetchone()
            if not row:
                return None
            conn.execute(
                """
                UPDATE lessons
                SET title = ?, description = ?, tags = ?, topics = ?, stage_id = ?, stage_name = ?, updated_at = ?
                WHERE lesson_id = ?
                """,
                (
                    title,
                    description,
                    json.dumps(tags),
                    json.dumps(topics),
                    stage_id,
                    stage_name,
                    now.isoformat(),
                    lesson_id,
                ),
            )
            refreshed = conn.execute(
                "SELECT * FROM lessons WHERE lesson_id = ?",
                (lesson_id,),
            ).fetchone()
        return self._serialize_lesson(refreshed)

    def delete_lesson(self, lesson_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT lesson_id FROM lessons WHERE lesson_id = ?",
                (lesson_id,),
            ).fetchone()
            if not row:
                return False
            conn.execute("DELETE FROM lessons WHERE lesson_id = ?", (lesson_id,))
        return True

    def list_lessons(
        self,
        project_id: str | None = None,
        query: str | None = None,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> list[LessonRecord]:
        with self._connect() as conn:
            if project_id:
                rows = conn.execute(
                    "SELECT * FROM lessons WHERE project_id = ? ORDER BY updated_at DESC",
                    (project_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM lessons ORDER BY updated_at DESC",
                ).fetchall()
        lessons = [self._serialize_lesson(row) for row in rows]

        if query:
            lowered = query.lower()
            lessons = [
                lesson
                for lesson in lessons
                if lowered in lesson.title.lower() or lowered in lesson.description.lower()
            ]
        if tags:
            tag_set = {tag.lower() for tag in tags}
            lessons = [
                lesson
                for lesson in lessons
                if tag_set.intersection({tag.lower() for tag in lesson.tags})
            ]
        if topics:
            topic_set = {topic.lower() for topic in topics}
            lessons = [
                lesson
                for lesson in lessons
                if topic_set.intersection({topic.lower() for topic in lesson.topics})
            ]
        return lessons

    def recommend_lessons(
        self,
        project_id: str,
        tags: list[str],
        topics: list[str],
        limit: int = 5,
    ) -> list[LessonRecord]:
        lessons = self.list_lessons(project_id)
        input_terms = {term.lower() for term in tags + topics if term}
        if not input_terms:
            return []

        scored: list[tuple[int, LessonRecord]] = []
        for lesson in lessons:
            lesson_terms = {term.lower() for term in lesson.tags + lesson.topics if term}
            overlap = len(input_terms.intersection(lesson_terms))
            if overlap:
                scored.append((overlap, lesson))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [lesson for _, lesson in scored[:limit]]
