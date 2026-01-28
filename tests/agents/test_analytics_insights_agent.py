import json

import pytest

from agents.runtime import InMemoryEventBus
from analytics_insights_agent import AnalyticsInsightsAgent


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
