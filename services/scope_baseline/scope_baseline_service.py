from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _db_path() -> Path:
    configured = os.getenv("SCOPE_BASELINE_DB_URL", "").strip()
    if configured.startswith("sqlite:///"):
        return Path(configured.removeprefix("sqlite:///"))
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "scope_baselines.db"


def _connect() -> sqlite3.Connection:
    db = _db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scope_baselines (
            baseline_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            version TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            data TEXT NOT NULL
        )
        """)
    conn.commit()
    return conn


def create_baseline(project_id: str, baseline_data: dict) -> str:
    """Persist a scope baseline and return its baseline ID."""
    baseline_id = baseline_data.get("baseline_id") or f"BL-{project_id}-{uuid.uuid4().hex[:8]}"
    created_at = baseline_data.get("timestamp") or baseline_data.get("created_at")
    timestamp = (
        created_at if isinstance(created_at, str) else datetime.now(timezone.utc).isoformat()
    )

    payload = (
        baseline_id,
        project_id,
        str(baseline_data.get("version", "1.0")),
        str(baseline_data.get("created_by", "system")),
        timestamp,
        json.dumps(baseline_data),
    )
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO scope_baselines (baseline_id, project_id, version, created_by, created_at, data)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(baseline_id)
            DO UPDATE SET
                project_id=excluded.project_id,
                version=excluded.version,
                created_by=excluded.created_by,
                created_at=excluded.created_at,
                data=excluded.data
            """,
            payload,
        )
        conn.commit()
    return baseline_id


def retrieve_baseline(baseline_id: str) -> dict:
    """Retrieve a persisted baseline by baseline ID."""
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT baseline_id, project_id, version, created_by, created_at, data
            FROM scope_baselines
            WHERE baseline_id = ?
            """,
            (baseline_id,),
        ).fetchone()
    if not row:
        raise ValueError(f"Baseline not found: {baseline_id}")

    return {
        "baseline_id": row[0],
        "project_id": row[1],
        "version": row[2],
        "created_by": row[3],
        "timestamp": row[4],
        "data": json.loads(row[5]),
    }


def list_baselines(project_id: str) -> list[dict]:
    """List baselines for a project, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT baseline_id, project_id, version, created_by, created_at, data
            FROM scope_baselines
            WHERE project_id = ?
            ORDER BY created_at DESC
            """,
            (project_id,),
        ).fetchall()

    return [
        {
            "baseline_id": row[0],
            "project_id": row[1],
            "version": row[2],
            "created_by": row[3],
            "timestamp": row[4],
            "data": json.loads(row[5]),
        }
        for row in rows
    ]
