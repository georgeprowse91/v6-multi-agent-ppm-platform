from __future__ import annotations

import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[3]
SRC_DIR = TESTS_DIR.parent / "src"
sys.path.extend(
    [
        str(SRC_DIR),
        str(REPO_ROOT),
        str(REPO_ROOT / "packages"),
        str(REPO_ROOT / "packages" / "security" / "src"),
    ]
)

from analytics_insights_agent import AnalyticsInsightsAgent


class DummyEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.published.append((topic, payload))


@pytest.mark.anyio
async def test_schedule_delay_kpi_updates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINEAGE_MASK_SALT", "test-salt")
    agent = AnalyticsInsightsAgent(
        config={
            "event_bus": DummyEventBus(),
            "analytics_output_store_path": tmp_path / "outputs.json",
            "analytics_alert_store_path": tmp_path / "alerts.json",
            "analytics_lineage_store_path": tmp_path / "lineage.json",
            "analytics_event_store_path": tmp_path / "events.json",
            "analytics_kpi_history_store_path": tmp_path / "kpi_history.json",
            "health_snapshot_store_path": tmp_path / "health.json",
        }
    )
    await agent._handle_domain_event(
        {"tenant_id": "tenant-a", "payload": {"delay_days": 6}}, "schedule.delay"
    )
    kpis = agent.analytics_output_store.list("tenant-a")
    schedule_kpi = next(
        record for record in kpis if record.get("name") == "Schedule Delay Average (days)"
    )
    assert schedule_kpi["current_value"] == 6
    assert schedule_kpi["threshold_status"]["breached"] is True


@pytest.mark.anyio
async def test_deployment_success_rate_kpi(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINEAGE_MASK_SALT", "test-salt")
    agent = AnalyticsInsightsAgent(
        config={
            "event_bus": DummyEventBus(),
            "analytics_output_store_path": tmp_path / "outputs.json",
            "analytics_alert_store_path": tmp_path / "alerts.json",
            "analytics_lineage_store_path": tmp_path / "lineage.json",
            "analytics_event_store_path": tmp_path / "events.json",
            "analytics_kpi_history_store_path": tmp_path / "kpi_history.json",
            "health_snapshot_store_path": tmp_path / "health.json",
            "kpi_definitions": [
                {
                    "name": "Deployment Success Rate",
                    "metric_name": "deployment.success_rate",
                    "target": 0.95,
                    "thresholds": {"min": 0.9},
                    "event_types": ["deployment.succeeded", "deployment.failed"],
                    "trend_direction": "higher_is_better",
                }
            ],
        }
    )
    await agent._handle_domain_event(
        {"tenant_id": "tenant-b", "payload": {"deployment_plan_id": "d1"}},
        "deployment.succeeded",
    )
    await agent._handle_domain_event(
        {"tenant_id": "tenant-b", "payload": {"deployment_plan_id": "d2"}},
        "deployment.failed",
    )
    result = await agent._compute_kpis_batch("tenant-b", None, None)
    assert result["kpis"][0]["current_value"] == pytest.approx(0.5)


@pytest.mark.anyio
async def test_ingest_sources_and_generate_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LINEAGE_MASK_SALT", "test-salt")
    agent = AnalyticsInsightsAgent(
        config={
            "event_bus": DummyEventBus(),
            "analytics_output_store_path": tmp_path / "outputs.json",
            "analytics_alert_store_path": tmp_path / "alerts.json",
            "analytics_lineage_store_path": tmp_path / "lineage.json",
            "analytics_event_store_path": tmp_path / "events.json",
            "analytics_kpi_history_store_path": tmp_path / "kpi_history.json",
            "health_snapshot_store_path": tmp_path / "health.json",
        }
    )
    ingestion = await agent._ingest_sources("tenant-c", ["jira"], {})
    assert ingestion["sources"] == ["jira"]
    assert ingestion["lineage_id"]
    await agent._handle_domain_event(
        {"tenant_id": "tenant-c", "payload": {"quality_score": 92}},
        "quality.metrics.calculated",
    )
    await agent._track_kpi(
        "tenant-c",
        {
            "name": "Quality Score",
            "metric_name": "quality.score.avg",
            "target": 90.0,
            "thresholds": {"min": 80.0},
        },
    )
    report = await agent._generate_report(
        "tenant-c", {"title": "KPI Summary", "type": "kpi_summary", "requester": "qa"}
    )
    assert report["visualizations"] >= 1
