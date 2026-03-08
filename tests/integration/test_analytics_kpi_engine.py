from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

SERVICE_SRC = Path(__file__).resolve().parents[2] / "services" / "analytics-service" / "src"
if str(SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(SERVICE_SRC))

from kpi_engine import (  # noqa: E402
    KpiSnapshot,
    apply_what_if_adjustments,
    compute_kpis_from_entities,
)


def test_compute_kpis_from_entities() -> None:
    work_items = [
        {
            "data": {
                "id": "wi-1",
                "project_id": "proj-1",
                "status": "done",
                "due_date": "2024-01-10",
            }
        },
        {
            "data": {
                "id": "wi-2",
                "project_id": "proj-1",
                "status": "in_progress",
                "due_date": "2024-01-05",
            }
        },
    ]
    budgets = [
        {
            "data": {
                "id": "budget-1",
                "portfolio_id": "proj-1",
                "amount": 1000,
                "metadata": {"actual_cost": 1100},
            }
        }
    ]
    risks = [
        {"data": {"id": "risk-1", "metadata": {"project_id": "proj-1"}, "impact": "high"}},
        {"data": {"id": "risk-2", "metadata": {"project_id": "proj-1"}, "impact": "low"}},
    ]
    resources = [
        {
            "data": {
                "id": "res-1",
                "metadata": {"project_id": "proj-1", "utilization": 0.8},
            }
        }
    ]

    metrics = compute_kpis_from_entities(
        project_id="proj-1",
        work_items=work_items,
        budgets=budgets,
        risks=risks,
        resources=resources,
    )

    assert metrics["schedule_variance"] < 0
    assert metrics["cost_variance"] == 0.1
    assert metrics["risk_score"] == 0.5
    assert metrics["resource_utilization"] == 0.8


def test_apply_what_if_adjustments() -> None:
    snapshot = KpiSnapshot(
        project_id="proj-1",
        tenant_id="tenant-a",
        computed_at=datetime.now(timezone.utc),
        metrics={
            "schedule_variance": -0.1,
            "cost_variance": 0.05,
            "risk_score": 0.2,
            "quality_score": 0.8,
            "resource_utilization": 0.9,
        },
        normalized={},
    )

    adjusted = apply_what_if_adjustments(
        snapshot,
        {"schedule_variance": 0.05, "risk_score": {"value": 0.1, "mode": "absolute"}},
    )

    assert adjusted.metrics["schedule_variance"] == -0.05
    assert adjusted.metrics["risk_score"] == 0.1
