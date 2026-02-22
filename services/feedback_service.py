"""Persistence service for agent feedback records."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from packages.feedback.feedback_models import Feedback
from packages.llm.src.llm.prompts import PromptRegistry


class FeedbackService:
    """Store and retrieve user feedback for offline analysis."""

    def __init__(self, db_path: str = "data/feedback.sqlite3") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.prompt_registry = PromptRegistry()
        self._initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    correlation_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    user_rating INTEGER NOT NULL CHECK(user_rating BETWEEN 1 AND 5),
                    comments TEXT NOT NULL,
                    corrected_response TEXT,
                    prompt_name TEXT,
                    prompt_version INTEGER,
                    created_at TEXT NOT NULL
                )
                """)
            existing_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(feedback)").fetchall()
            }
            if "prompt_name" not in existing_columns:
                connection.execute("ALTER TABLE feedback ADD COLUMN prompt_name TEXT")
            if "prompt_version" not in existing_columns:
                connection.execute("ALTER TABLE feedback ADD COLUMN prompt_version INTEGER")
            connection.commit()

    def save_feedback(self, feedback: Feedback) -> None:
        payload = asdict(feedback)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO feedback (
                    correlation_id,
                    agent_id,
                    user_rating,
                    comments,
                    corrected_response,
                    prompt_name,
                    prompt_version,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["correlation_id"],
                    payload["agent_id"],
                    payload["user_rating"],
                    payload["comments"],
                    payload["corrected_response"],
                    payload["prompt_name"],
                    payload["prompt_version"],
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            connection.commit()

        if (
            payload["user_rating"] <= 2
            and payload["prompt_name"]
            and payload["prompt_version"] is not None
        ):
            reason = f"Auto-flagged from feedback correlation={payload['correlation_id']} rating={payload['user_rating']}"
            self.prompt_registry.flag_prompt_version(
                payload["prompt_name"],
                int(payload["prompt_version"]),
                reason,
            )

    def fetch_by_correlation_id(self, correlation_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT correlation_id, agent_id, user_rating, comments, corrected_response, prompt_name, prompt_version, created_at
                FROM feedback
                WHERE correlation_id = ?
                ORDER BY id ASC
                """,
                (correlation_id,),
            ).fetchall()
        return [dict(row) for row in rows]
