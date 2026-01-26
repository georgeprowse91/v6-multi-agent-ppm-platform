from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class ScheduledJob:
    job_id: str
    name: str
    interval_minutes: int
    tenant_id: str
    payload: dict[str, Any]
    enabled: bool
    next_run: datetime
    last_run: datetime | None
    status: str


class AnalyticsScheduler:
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
                CREATE TABLE IF NOT EXISTS analytics_jobs (
                    job_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    interval_minutes INTEGER NOT NULL,
                    tenant_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    next_run TEXT NOT NULL,
                    last_run TEXT,
                    status TEXT NOT NULL
                )
                """
            )

    def _serialize_job(self, row: sqlite3.Row) -> ScheduledJob:
        return ScheduledJob(
            job_id=row["job_id"],
            name=row["name"],
            interval_minutes=row["interval_minutes"],
            tenant_id=row["tenant_id"],
            payload=json.loads(row["payload"]),
            enabled=bool(row["enabled"]),
            next_run=datetime.fromisoformat(row["next_run"]),
            last_run=datetime.fromisoformat(row["last_run"]) if row["last_run"] else None,
            status=row["status"],
        )

    def schedule_job(
        self,
        name: str,
        interval_minutes: int,
        tenant_id: str,
        payload: dict[str, Any],
    ) -> ScheduledJob:
        now = datetime.now(timezone.utc)
        job_id = str(uuid4())
        next_run = now + timedelta(minutes=interval_minutes)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO analytics_jobs
                    (job_id, name, interval_minutes, tenant_id, payload, enabled, next_run, last_run, status)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    name,
                    interval_minutes,
                    tenant_id,
                    json.dumps(payload),
                    1,
                    next_run.isoformat(),
                    None,
                    "scheduled",
                ),
            )
        return ScheduledJob(
            job_id=job_id,
            name=name,
            interval_minutes=interval_minutes,
            tenant_id=tenant_id,
            payload=payload,
            enabled=True,
            next_run=next_run,
            last_run=None,
            status="scheduled",
        )

    def list_jobs(self, tenant_id: str) -> list[ScheduledJob]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM analytics_jobs WHERE tenant_id = ? ORDER BY name", (tenant_id,)
            ).fetchall()
        return [self._serialize_job(row) for row in rows]

    def get_job(self, job_id: str, tenant_id: str) -> ScheduledJob | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM analytics_jobs WHERE job_id = ? AND tenant_id = ?",
                (job_id, tenant_id),
            ).fetchone()
        return self._serialize_job(row) if row else None

    def update_job(
        self,
        job_id: str,
        tenant_id: str,
        interval_minutes: int | None = None,
        enabled: bool | None = None,
    ) -> ScheduledJob | None:
        job = self.get_job(job_id, tenant_id)
        if not job:
            return None
        interval_minutes = interval_minutes or job.interval_minutes
        enabled = job.enabled if enabled is None else enabled
        next_run = job.next_run
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE analytics_jobs
                SET interval_minutes = ?, enabled = ?, next_run = ?
                WHERE job_id = ? AND tenant_id = ?
                """,
                (
                    interval_minutes,
                    1 if enabled else 0,
                    next_run.isoformat(),
                    job_id,
                    tenant_id,
                ),
            )
        return self.get_job(job_id, tenant_id)

    def due_jobs(self, now: datetime | None = None) -> list[ScheduledJob]:
        now = now or datetime.now(timezone.utc)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM analytics_jobs
                WHERE enabled = 1 AND next_run <= ?
                ORDER BY next_run
                """,
                (now.isoformat(),),
            ).fetchall()
        return [self._serialize_job(row) for row in rows]

    def record_run(self, job: ScheduledJob, status: str) -> ScheduledJob:
        now = datetime.now(timezone.utc)
        next_run = now + timedelta(minutes=job.interval_minutes)
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE analytics_jobs
                SET last_run = ?, next_run = ?, status = ?
                WHERE job_id = ?
                """,
                (
                    now.isoformat(),
                    next_run.isoformat(),
                    status,
                    job.job_id,
                ),
            )
        return ScheduledJob(
            job_id=job.job_id,
            name=job.name,
            interval_minutes=job.interval_minutes,
            tenant_id=job.tenant_id,
            payload=job.payload,
            enabled=job.enabled,
            next_run=next_run,
            last_run=now,
            status=status,
        )
