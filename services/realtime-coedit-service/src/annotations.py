"""Agent annotation model and store for collaborative editing sessions.

Production-grade implementation:
- SQLite-backed persistence for durability and query performance
- LLM-powered annotation suggestion generation
- Agent-specific suggestion routing based on content analysis
- Thread-safe operations via SQLite's built-in locking
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from pydantic import BaseModel, Field

logger = logging.getLogger("coedit.annotations")

# Persistence
_STORAGE_DIR = Path(os.getenv("ANNOTATION_STORAGE_DIR", "/tmp/ppm-annotations"))
_DB_PATH = _STORAGE_DIR / "annotations.db"


class Annotation(BaseModel):
    """An AI agent annotation attached to a canvas block within a coedit session."""

    annotation_id: str = Field(default_factory=lambda: f"ann-{uuid.uuid4().hex[:8]}")
    session_id: str = ""
    agent_id: str = ""
    agent_name: str = ""
    block_id: str = ""
    content: str = ""
    annotation_type: str = "suggestion"  # suggestion, warning, insight, quality
    created_at: float = Field(default_factory=time.time)
    dismissed: bool = False
    applied: bool = False


_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS annotations (
    annotation_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    agent_id TEXT DEFAULT '',
    agent_name TEXT DEFAULT '',
    block_id TEXT DEFAULT '',
    content TEXT DEFAULT '',
    annotation_type TEXT DEFAULT 'suggestion',
    created_at REAL NOT NULL,
    dismissed INTEGER DEFAULT 0,
    applied INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_annotations_session ON annotations(session_id);
CREATE INDEX IF NOT EXISTS idx_annotations_block ON annotations(session_id, block_id);
"""


class AnnotationStore:
    """SQLite-backed annotation store with in-memory fallback."""

    def __init__(self, db_path: Path | None = None, persist: bool = True) -> None:
        self._persist = persist
        self._db_path = db_path or _DB_PATH
        self._fallback_store: dict[str, list[Annotation]] = {}
        self._db_initialized = False

    @contextmanager
    def _get_conn(self) -> Iterator[sqlite3.Connection]:
        """Get a SQLite connection with automatic table creation."""
        if not self._persist:
            raise sqlite3.OperationalError("Persistence disabled")

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            if not self._db_initialized:
                conn.executescript(_CREATE_TABLE_SQL)
                self._db_initialized = True
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _to_annotation(self, row: sqlite3.Row) -> Annotation:
        return Annotation(
            annotation_id=row["annotation_id"],
            session_id=row["session_id"],
            agent_id=row["agent_id"],
            agent_name=row["agent_name"],
            block_id=row["block_id"],
            content=row["content"],
            annotation_type=row["annotation_type"],
            created_at=row["created_at"],
            dismissed=bool(row["dismissed"]),
            applied=bool(row["applied"]),
        )

    def create_annotation(self, session_id: str, annotation: Annotation) -> Annotation:
        annotation.session_id = session_id
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO annotations (annotation_id, session_id, agent_id, agent_name, "
                    "block_id, content, annotation_type, created_at, dismissed, applied) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        annotation.annotation_id, session_id, annotation.agent_id,
                        annotation.agent_name, annotation.block_id, annotation.content,
                        annotation.annotation_type, annotation.created_at,
                        int(annotation.dismissed), int(annotation.applied),
                    ),
                )
                return annotation
        except (sqlite3.OperationalError, OSError):
            # Fallback to in-memory
            self._fallback_store.setdefault(session_id, []).append(annotation)
            return annotation

    def list_annotations(self, session_id: str, active_only: bool = True) -> list[Annotation]:
        try:
            with self._get_conn() as conn:
                if active_only:
                    rows = conn.execute(
                        "SELECT * FROM annotations WHERE session_id = ? AND dismissed = 0 ORDER BY created_at",
                        (session_id,),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM annotations WHERE session_id = ? ORDER BY created_at",
                        (session_id,),
                    ).fetchall()
                return [self._to_annotation(row) for row in rows]
        except (sqlite3.OperationalError, OSError):
            annotations = self._fallback_store.get(session_id, [])
            if active_only:
                return [a for a in annotations if not a.dismissed]
            return list(annotations)

    def dismiss_annotation(self, annotation_id: str) -> Annotation | None:
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE annotations SET dismissed = 1 WHERE annotation_id = ?",
                    (annotation_id,),
                )
                row = conn.execute(
                    "SELECT * FROM annotations WHERE annotation_id = ?",
                    (annotation_id,),
                ).fetchone()
                return self._to_annotation(row) if row else None
        except (sqlite3.OperationalError, OSError):
            for annotations in self._fallback_store.values():
                for ann in annotations:
                    if ann.annotation_id == annotation_id:
                        ann.dismissed = True
                        return ann
            return None

    def apply_annotation(self, annotation_id: str) -> Annotation | None:
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE annotations SET applied = 1 WHERE annotation_id = ?",
                    (annotation_id,),
                )
                row = conn.execute(
                    "SELECT * FROM annotations WHERE annotation_id = ?",
                    (annotation_id,),
                ).fetchone()
                return self._to_annotation(row) if row else None
        except (sqlite3.OperationalError, OSError):
            for annotations in self._fallback_store.values():
                for ann in annotations:
                    if ann.annotation_id == annotation_id:
                        ann.applied = True
                        return ann
            return None


_annotation_store = AnnotationStore()


def get_annotation_store() -> AnnotationStore:
    return _annotation_store


# ---------------------------------------------------------------------------
# LLM-powered annotation suggestions
# ---------------------------------------------------------------------------

# Agent routing rules — maps content signals to specialized agents
_AGENT_SIGNALS: list[dict[str, Any]] = [
    {
        "agent_id": "risk-management",
        "agent_name": "Risk Agent",
        "keywords": ["risk", "threat", "vulnerability", "concern", "mitigation", "exposure"],
        "annotation_type": "suggestion",
        "template": "Consider adding a risk mitigation strategy and assigning a risk owner for the identified risk.",
    },
    {
        "agent_id": "financial-management",
        "agent_name": "Finance Agent",
        "keywords": ["budget", "cost", "expense", "spending", "revenue", "roi", "npv"],
        "annotation_type": "insight",
        "template": "Financial items detected. Consider linking to the project budget baseline for variance tracking.",
    },
    {
        "agent_id": "schedule-planning",
        "agent_name": "Schedule Agent",
        "keywords": ["deadline", "overdue", "delay", "behind schedule", "milestone", "timeline"],
        "annotation_type": "warning",
        "template": "Schedule concern detected. Review the critical path and consider resource reallocation.",
    },
    {
        "agent_id": "quality-management",
        "agent_name": "Quality Agent",
        "keywords": ["quality", "defect", "bug", "issue", "test", "acceptance criteria"],
        "annotation_type": "suggestion",
        "template": "Quality issue referenced. Consider adding acceptance criteria and linking to the quality register.",
    },
    {
        "agent_id": "compliance-governance",
        "agent_name": "Compliance Agent",
        "keywords": ["compliance", "regulation", "gdpr", "sox", "hipaa", "audit", "privacy"],
        "annotation_type": "warning",
        "template": "Compliance-related content detected. Ensure regulatory requirements are tracked and evidence collected.",
    },
    {
        "agent_id": "knowledge-management",
        "agent_name": "Knowledge Agent",
        "keywords": [],  # triggered by content length
        "annotation_type": "quality",
        "template": "This block contains substantial content. Consider breaking it into smaller, focused sections.",
    },
]


async def generate_suggestions(
    session_id: str,
    block_id: str,
    block_content: str,
    context: dict[str, Any] | None = None,
) -> list[Annotation]:
    """Generate AI-powered annotation suggestions for a block.

    Uses LLM when available, falls back to rule-based agent routing.
    """
    suggestions: list[Annotation] = []

    # Try LLM-powered suggestions
    try:
        llm_result = await _llm_suggest(block_content, context or {})
        if isinstance(llm_result, list):
            for item in llm_result:
                if isinstance(item, dict) and item.get("content"):
                    ann = Annotation(
                        session_id=session_id,
                        agent_id=item.get("agent_id", "quality-management"),
                        agent_name=item.get("agent_name", "Quality Agent"),
                        block_id=block_id,
                        content=item["content"],
                        annotation_type=item.get("type", "suggestion"),
                    )
                    suggestions.append(ann)
            if suggestions:
                return suggestions
    except Exception as exc:
        logger.debug("LLM suggestion failed: %s", exc)

    # Fallback: rule-based agent routing
    content_lower = block_content.lower()

    for signal in _AGENT_SIGNALS:
        if signal["keywords"]:
            if any(kw in content_lower for kw in signal["keywords"]):
                suggestions.append(Annotation(
                    session_id=session_id,
                    agent_id=signal["agent_id"],
                    agent_name=signal["agent_name"],
                    block_id=block_id,
                    content=signal["template"],
                    annotation_type=signal["annotation_type"],
                ))
        elif len(block_content) > 500:
            # Knowledge agent triggered by content length
            suggestions.append(Annotation(
                session_id=session_id,
                agent_id=signal["agent_id"],
                agent_name=signal["agent_name"],
                block_id=block_id,
                content=signal["template"],
                annotation_type=signal["annotation_type"],
            ))

    return suggestions


async def _llm_suggest(content: str, context: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Call LLM for annotation suggestions."""
    try:
        from llm.client import LLMGateway

        provider = os.getenv("LLM_PROVIDER", "mock")
        config: dict[str, Any] = {}
        if provider == "mock":
            config["demo_mode"] = True
        gateway = LLMGateway(provider=provider, config=config)

        system = (
            "You are an AI assistant for collaborative project editing. "
            "Analyze the content block and generate helpful annotations. "
            "Return a JSON array: "
            '[{"content":"...","type":"suggestion|warning|insight|quality",'
            '"agent_id":"...","agent_name":"..."}]. '
            "Available agents: risk-management, financial-management, "
            "schedule-planning, quality-management, knowledge-management, "
            "compliance-governance. Generate 1-3 annotations."
        )
        user = f"Content block:\n{content[:1000]}\n\nContext: {json.dumps(context)}"

        response = await gateway.complete(system, user, json_mode=True)
        raw = response.content.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            raw = "\n".join(lines)
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "annotations" in parsed:
            return parsed["annotations"]
    except Exception as exc:
        logger.debug("LLM suggest call failed: %s", exc)

    return None
