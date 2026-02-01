from __future__ import annotations

import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[3]
SRC_DIR = TESTS_DIR.parent / "src"
AGENT_22_SRC = (
    REPO_ROOT
    / "agents"
    / "operations-management"
    / "agent-22-analytics-insights"
    / "src"
)

sys.path.extend(
    [
        str(SRC_DIR),
        str(AGENT_22_SRC),
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

    def subscribe(self, _topic: str, _handler) -> None:
        return None


class DummySynapseManager:
    def __init__(self) -> None:
        self.datasets: list[tuple[str, list[dict[str, object]]]] = []

    def ingest_dataset(self, dataset_name: str, payload: list[dict[str, object]]) -> dict[str, object]:
        self.datasets.append((dataset_name, payload))
        return {"dataset": dataset_name, "stored": True}


@pytest.mark.anyio
async def test_kpi_definitions_include_required(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    names = {kpi.get("name") for kpi in agent.kpi_definitions}
    assert "Schedule Adherence (%)" in names
    assert "Cost Variance (%)" in names
    assert "Program Performance Index" in names
    assert "Defect Density" in names
    assert "Compliance Level" in names
    assert "System Health Score" in names


@pytest.mark.anyio
async def test_ingest_metrics_redacts_and_stores(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINEAGE_MASK_SALT", "test-salt")
    synapse_manager = DummySynapseManager()
    agent = AnalyticsInsightsAgent(
        config={
            "event_bus": DummyEventBus(),
            "synapse_manager": synapse_manager,
            "analytics_output_store_path": tmp_path / "outputs.json",
            "analytics_alert_store_path": tmp_path / "alerts.json",
            "analytics_lineage_store_path": tmp_path / "lineage.json",
            "analytics_event_store_path": tmp_path / "events.json",
            "analytics_kpi_history_store_path": tmp_path / "kpi_history.json",
            "health_snapshot_store_path": tmp_path / "health.json",
        }
    )
    result = await agent._ingest_metrics(
        "tenant-x",
        [
            {
                "event_type": "schedule.delay",
                "payload": {"delay_days": 3, "email": "user@example.com"},
            }
        ],
        [{"metric": "schedule.delay", "value": 3}],
    )
    assert result["synapse"]["stored"] is True
    stored_events = agent.analytics_event_store.list("tenant-x")
    assert stored_events[0]["payload"]["email"] != "user@example.com"
    assert synapse_manager.datasets


@pytest.mark.anyio
async def test_get_kpi_trends(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
        {"tenant_id": "tenant-y", "payload": {"adherence": 0.92}},
        "schedule.baseline.locked",
    )
    kpi_result = await agent._track_kpi(
        "tenant-y",
        {
            "name": "Schedule Adherence (%)",
            "metric_name": "schedule.adherence",
            "target": 0.95,
            "thresholds": {"min": 0.9},
        },
    )
    response = await agent.process(
        {"action": "get_kpi_trends", "tenant_id": "tenant-y", "kpi_ids": [kpi_result["kpi_id"]]}
    )
    assert response["trends"][0]["entries"]


@pytest.mark.anyio
async def test_get_forecasts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    response = await agent.process(
        {
            "action": "get_forecasts",
            "tenant_id": "tenant-z",
            "forecast_requests": [
                {"model_type": "project_success", "input_data": {"risk_score": 0.2}}
            ],
        }
    )
    assert response["forecasts"][0]["model_type"] == "project_success"
    assert response["forecasts"][0]["prediction"] is not None
