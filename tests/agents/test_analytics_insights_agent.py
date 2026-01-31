import json
from unittest.mock import AsyncMock

import pytest
from analytics_insights_agent import AnalyticsInsightsAgent

from agents.runtime import InMemoryEventBus


@pytest.mark.asyncio
async def test_analytics_persists_outputs_and_masks_lineage(tmp_path, monkeypatch):
    monkeypatch.setenv("LINEAGE_MASK_SALT", "unit-test-salt")
    event_bus = InMemoryEventBus()
    agent = AnalyticsInsightsAgent(
        config={
            "analytics_output_store_path": tmp_path / "outputs.json",
            "analytics_alert_store_path": tmp_path / "alerts.json",
            "analytics_lineage_store_path": tmp_path / "lineage.json",
            "health_snapshot_store_path": tmp_path / "health.json",
            "event_bus": event_bus,
        }
    )
    await agent.initialize()

    dashboard = await agent.process(
        {
            "action": "create_dashboard",
            "tenant_id": "tenant-analytics",
            "dashboard": {"name": "Exec View", "widgets": []},
        }
    )
    assert agent.analytics_output_store.get("tenant-analytics", dashboard["dashboard_id"])

    lineage = await agent.process(
        {
            "action": "update_data_lineage",
            "tenant_id": "tenant-analytics",
            "lineage": {
                "sources": ["crm"],
                "transformations": [{"actor": {"email": "jane.doe@example.com"}}],
                "target": "executive_summary",
            },
        }
    )

    stored_lineage = agent.analytics_lineage_store.get("tenant-analytics", lineage["lineage_id"])
    assert stored_lineage is not None
    assert "jane.doe@example.com" not in json.dumps(stored_lineage)


@pytest.mark.asyncio
async def test_analytics_get_insights_success(tmp_path):
    event_bus = InMemoryEventBus()
    agent = AnalyticsInsightsAgent(
        config={
            "analytics_output_store_path": tmp_path / "outputs.json",
            "analytics_alert_store_path": tmp_path / "alerts.json",
            "health_snapshot_store_path": tmp_path / "health.json",
            "event_bus": event_bus,
        }
    )
    await agent.initialize()

    response = await agent.process({"action": "get_insights", "tenant_id": "tenant-analytics"})

    assert "insights" in response


@pytest.mark.asyncio
async def test_analytics_rejects_invalid_action(tmp_path):
    agent = AnalyticsInsightsAgent(
        config={
            "analytics_output_store_path": tmp_path / "outputs.json",
            "analytics_alert_store_path": tmp_path / "alerts.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "unknown"})

    assert valid is False


@pytest.mark.asyncio
async def test_analytics_rejects_missing_dashboard(tmp_path):
    agent = AnalyticsInsightsAgent(
        config={
            "analytics_output_store_path": tmp_path / "outputs.json",
            "analytics_alert_store_path": tmp_path / "alerts.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "create_dashboard"})

    assert valid is False


@pytest.mark.asyncio
async def test_analytics_health_summary_report(tmp_path):
    event_bus = InMemoryEventBus()
    agent = AnalyticsInsightsAgent(
        config={
            "analytics_output_store_path": tmp_path / "outputs.json",
            "analytics_alert_store_path": tmp_path / "alerts.json",
            "health_snapshot_store_path": tmp_path / "health.json",
            "event_bus": event_bus,
        }
    )
    await agent.initialize()

    await event_bus.publish(
        "project.health.updated",
        {
            "tenant_id": "tenant-analytics",
            "payload": {
                "health_data": {
                    "project_id": "proj-1",
                    "composite_score": 0.82,
                    "health_status": "At Risk",
                    "metrics": {
                        "schedule": {"score": 0.7},
                        "cost": {"score": 0.8},
                        "risk": {"score": 0.6},
                        "quality": {"score": 0.9},
                        "resource": {"score": 0.85},
                    },
                    "monitored_at": "2024-03-01T00:00:00",
                }
            },
        },
    )

    report = await agent.process(
        {
            "action": "generate_report",
            "tenant_id": "tenant-analytics",
            "report": {"title": "Portfolio Health", "type": "health_summary"},
        }
    )

    assert report["report_id"]


@pytest.mark.asyncio
async def test_analytics_kpi_threshold_alerts(tmp_path):
    events: list[dict] = []

    def capture_event(payload: dict) -> None:
        events.append(payload)

    event_bus = InMemoryEventBus()
    event_bus.subscribe("analytics.kpi.threshold_breached", capture_event)
    agent = AnalyticsInsightsAgent(
        config={
            "analytics_output_store_path": tmp_path / "outputs.json",
            "analytics_alert_store_path": tmp_path / "alerts.json",
            "health_snapshot_store_path": tmp_path / "health.json",
            "event_bus": event_bus,
        }
    )
    await agent.initialize()

    response = await agent.process(
        {
            "action": "track_kpi",
            "tenant_id": "tenant-analytics",
            "kpi": {"name": "Delivery Velocity", "thresholds": {"max": 80}},
        }
    )

    assert response["alerts_triggered"]
    alerts = agent.analytics_alert_store.list("tenant-analytics")
    assert alerts
    assert events


@pytest.mark.asyncio
async def test_analytics_initializes_synapse_pools(tmp_path):
    class SynapseStub:
        def __init__(self) -> None:
            self.called = False

        def create_sql_pool(self, workspace: str, pool: str) -> None:
            self.called = True

        def create_spark_pool(self, workspace: str, pool: str) -> None:
            self.called = True

    synapse_stub = SynapseStub()
    agent = AnalyticsInsightsAgent(
        config={
            "analytics_output_store_path": tmp_path / "outputs.json",
            "analytics_alert_store_path": tmp_path / "alerts.json",
            "synapse_workspace_name": "synapse-ws",
            "synapse_sql_pool_name": "sql-pool",
            "synapse_client": synapse_stub,
        }
    )
    await agent.initialize()

    assert synapse_stub.called is True


@pytest.mark.asyncio
async def test_analytics_prediction_uses_ml_manager(tmp_path):
    ml_manager = AsyncMock()
    ml_manager.load_model.return_value = {"model_type": "cost_overrun", "version": "1.0"}
    agent = AnalyticsInsightsAgent(
        config={
            "analytics_output_store_path": tmp_path / "outputs.json",
            "analytics_alert_store_path": tmp_path / "alerts.json",
            "ml_manager": ml_manager,
        }
    )
    await agent.initialize()

    await agent.process(
        {
            "action": "run_prediction",
            "tenant_id": "tenant-analytics",
            "model_type": "cost_overrun",
            "input_data": {"project_id": "proj-123", "current_cost": 100},
        }
    )

    ml_manager.load_model.assert_awaited_with("cost_overrun")


@pytest.mark.asyncio
async def test_analytics_narrative_generation_uses_service(tmp_path):
    narrative_service = AsyncMock()
    narrative_service.generate_narrative.return_value = "Narrative summary"
    agent = AnalyticsInsightsAgent(
        config={
            "analytics_output_store_path": tmp_path / "outputs.json",
            "analytics_alert_store_path": tmp_path / "alerts.json",
            "narrative_service": narrative_service,
        }
    )
    await agent.initialize()

    response = await agent.process(
        {"action": "generate_narrative", "tenant_id": "tenant-analytics", "data": {}}
    )

    assert response["content"] == "Narrative summary"
    narrative_service.generate_narrative.assert_awaited()


@pytest.mark.asyncio
async def test_analytics_scenario_analysis_uses_predictions(tmp_path):
    agent = AnalyticsInsightsAgent(
        config={
            "analytics_output_store_path": tmp_path / "outputs.json",
            "analytics_alert_store_path": tmp_path / "alerts.json",
        }
    )
    agent._run_prediction = AsyncMock(
        return_value={"prediction": 0.3, "confidence": 0.8}
    )
    await agent.initialize()

    response = await agent.process(
        {
            "action": "scenario_analysis",
            "tenant_id": "tenant-analytics",
            "scenario": {
                "name": "Budget Increase",
                "parameters": {
                    "assumptions": {"budget": 100000},
                    "kpi_models": [{"model_type": "schedule_slip", "input_data": {}}],
                },
            },
        }
    )

    assert response["scenario_metrics"]["schedule_slip"] == 0.3
    agent._run_prediction.assert_awaited()
