from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class KpiSnapshot:
    tenant_id: str
    project_id: str
    captured_at: datetime
    metrics: dict[str, float | None]


class MetricsStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kpi_metrics (
                    tenant_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    metrics_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_kpi_metrics
                ON kpi_metrics (tenant_id, project_id, captured_at)
                """
            )
            conn.commit()

    def add_snapshot(
        self,
        tenant_id: str,
        project_id: str,
        metrics: dict[str, float | None],
        captured_at: datetime | None = None,
    ) -> KpiSnapshot:
        captured_at = captured_at or datetime.now(timezone.utc)
        payload = json.dumps(metrics)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO kpi_metrics (tenant_id, project_id, captured_at, metrics_json) "
                "VALUES (?, ?, ?, ?)",
                (tenant_id, project_id, captured_at.isoformat(), payload),
            )
            conn.commit()
        return KpiSnapshot(
            tenant_id=tenant_id,
            project_id=project_id,
            captured_at=captured_at,
            metrics=metrics,
        )

    def list_snapshots(self, tenant_id: str, project_id: str, limit: int = 50) -> list[KpiSnapshot]:
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                """
                SELECT tenant_id, project_id, captured_at, metrics_json
                FROM kpi_metrics
                WHERE tenant_id = ? AND project_id = ?
                ORDER BY captured_at ASC
                LIMIT ?
                """,
                (tenant_id, project_id, limit),
            ).fetchall()
        snapshots: list[KpiSnapshot] = []
        for tenant_id, project_id, captured_at, metrics_json in rows:
            snapshots.append(
                KpiSnapshot(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    captured_at=datetime.fromisoformat(captured_at),
                    metrics=_parse_metrics(metrics_json),
                )
            )
        return snapshots


def _parse_metrics(payload: str) -> dict[str, float | None]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    if isinstance(data, dict):
        return {key: _coerce_metric(value) for key, value in data.items()}
    return {}


def _coerce_metric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
