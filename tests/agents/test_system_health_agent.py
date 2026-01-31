import json
from datetime import datetime, timedelta

import pytest
import system_health_agent as system_health_module
from system_health_agent import SystemHealthAgent


@pytest.mark.asyncio
async def test_system_health_persists_alerts_and_redacts_pii(tmp_path):
    agent = SystemHealthAgent(
        config={
            "alert_store_path": tmp_path / "alerts.json",
            "incident_store_path": tmp_path / "incidents.json",
        }
    )
    await agent.initialize()

    alert = await agent.process(
        {
            "action": "create_alert",
            "tenant_id": "tenant-health",
            "alert": {
                "name": "Email alerts for jane.doe@example.com",
                "description": "Contact jane.doe@example.com for escalation",
                "service_name": "api",
                "condition": "error_rate",
            },
        }
    )
    stored_alert = agent.alert_store.get("tenant-health", alert["alert_id"])
    assert stored_alert is not None
    assert "jane.doe@example.com" not in json.dumps(stored_alert)

    incident = await agent.process(
        {
            "action": "create_incident",
            "tenant_id": "tenant-health",
            "incident": {
                "title": "Pager duty for +1 (555) 555-0101",
                "description": "Call +1 (555) 555-0101 if needed",
                "severity": "high",
                "reporter": "ops@example.com",
            },
        }
    )
    stored_incident = agent.incident_store.get("tenant-health", incident["incident_id"])
    assert stored_incident is not None
    assert "555-0101" not in json.dumps(stored_incident)


@pytest.mark.asyncio
async def test_system_health_status_success(tmp_path):
    agent = SystemHealthAgent(
        config={
            "alert_store_path": tmp_path / "alerts.json",
            "incident_store_path": tmp_path / "incidents.json",
        }
    )
    await agent.initialize()

    response = await agent.process({"action": "get_system_status", "tenant_id": "tenant-health"})

    assert response["overall_status"] in {"healthy", "degraded", "critical"}


@pytest.mark.asyncio
async def test_system_health_collect_metrics_triggers_alerts(tmp_path):
    agent = SystemHealthAgent(
        config={
            "alert_store_path": tmp_path / "alerts.json",
            "incident_store_path": tmp_path / "incidents.json",
            "alert_threshold_error_rate": 0.05,
            "alert_threshold_response_time_ms": 500,
        }
    )
    await agent.initialize()

    response = await agent.process(
        {
            "action": "collect_metrics",
            "tenant_id": "tenant-health",
            "service_name": "api",
            "metrics": {"error_rate": 0.2, "response_time_ms": 900},
        }
    )

    assert response["alerts_triggered"]
    alerts = agent.alert_store.list("tenant-health")
    assert len(alerts) >= 2


@pytest.mark.asyncio
async def test_system_health_validation_rejects_invalid_action(tmp_path):
    agent = SystemHealthAgent(
        config={
            "alert_store_path": tmp_path / "alerts.json",
            "incident_store_path": tmp_path / "incidents.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_system_health_validation_rejects_missing_action(tmp_path):
    agent = SystemHealthAgent(
        config={
            "alert_store_path": tmp_path / "alerts.json",
            "incident_store_path": tmp_path / "incidents.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({})

    assert valid is False


@pytest.mark.asyncio
async def test_system_health_exposes_health_endpoints(tmp_path):
    agent = SystemHealthAgent(
        config={
            "alert_store_path": tmp_path / "alerts.json",
            "incident_store_path": tmp_path / "incidents.json",
            "health_endpoints": [{"name": "api", "url": "https://example.com/health"}],
        }
    )
    await agent.initialize()

    response = await agent.process({"action": "get_health_endpoints"})

    assert response["total_endpoints"] == 1


@pytest.mark.asyncio
async def test_system_health_initializes_azure_monitor(monkeypatch, tmp_path):
    calls = {}

    def fake_configure_azure_monitor(connection_string: str) -> None:
        calls["connection_string"] = connection_string

    monkeypatch.setenv("APPINSIGHTS_INSTRUMENTATION_KEY", "appinsights-key")
    monkeypatch.setenv("MONITOR_WORKSPACE_ID", "workspace-id")
    monkeypatch.setattr(system_health_module, "_configure_azure_monitor", fake_configure_azure_monitor)

    agent = SystemHealthAgent(
        config={
            "alert_store_path": tmp_path / "alerts.json",
            "incident_store_path": tmp_path / "incidents.json",
        }
    )
    await agent.initialize()

    assert calls["connection_string"] == "InstrumentationKey=appinsights-key"


@pytest.mark.asyncio
async def test_system_health_anomaly_detection_flags_outliers(tmp_path):
    agent = SystemHealthAgent(
        config={
            "alert_store_path": tmp_path / "alerts.json",
            "incident_store_path": tmp_path / "incidents.json",
        }
    )
    await agent.initialize()

    start = datetime.utcnow() - timedelta(minutes=5)
    metrics = [
        {"metric": "latency_ms", "value": 100, "timestamp": start.isoformat()},
        {
            "metric": "latency_ms",
            "value": 110,
            "timestamp": (start + timedelta(minutes=1)).isoformat(),
        },
        {"metric": "latency_ms", "value": 95, "timestamp": (start + timedelta(minutes=2)).isoformat()},
        {
            "metric": "latency_ms",
            "value": 105,
            "timestamp": (start + timedelta(minutes=3)).isoformat(),
        },
        {"metric": "latency_ms", "value": 98, "timestamp": (start + timedelta(minutes=4)).isoformat()},
        {"metric": "latency_ms", "value": 900, "timestamp": (start + timedelta(minutes=5)).isoformat()},
    ]

    anomalies = await agent._apply_anomaly_detection(metrics)

    assert anomalies
    assert anomalies[0]["metric"] == "latency_ms"


@pytest.mark.asyncio
async def test_system_health_incident_integrations_triggered(monkeypatch, tmp_path):
    calls = []

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            calls.append((url, json))

    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: DummyClient())

    agent = SystemHealthAgent(
        config={
            "alert_store_path": tmp_path / "alerts.json",
            "incident_store_path": tmp_path / "incidents.json",
            "pagerduty_webhook_url": "https://pagerduty.example/incident",
            "opsgenie_webhook_url": "https://opsgenie.example/incident",
        }
    )
    await agent.initialize()

    await agent.process(
        {
            "action": "create_incident",
            "tenant_id": "tenant-health",
            "incident": {"title": "Database error", "severity": "critical"},
        }
    )

    assert len(calls) == 2
    assert calls[0][1]["event_type"] == "incident"


@pytest.mark.asyncio
async def test_system_health_scaling_triggers_webhook(monkeypatch, tmp_path):
    calls = []

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            calls.append((url, json))

    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: DummyClient())

    agent = SystemHealthAgent(
        config={
            "alert_store_path": tmp_path / "alerts.json",
            "incident_store_path": tmp_path / "incidents.json",
            "scaling_webhook_url": "https://automation.example/scale",
            "scaling_threshold_cpu": 0.5,
        }
    )
    await agent.initialize()

    await agent.process(
        {
            "action": "collect_metrics",
            "tenant_id": "tenant-health",
            "service_name": "api",
            "metrics": {"cpu_usage": 0.9},
        }
    )

    assert calls
    assert calls[0][0] == "https://automation.example/scale"


@pytest.mark.asyncio
async def test_system_health_query_and_forecast(monkeypatch, tmp_path):
    agent = SystemHealthAgent(
        config={
            "alert_store_path": tmp_path / "alerts.json",
            "incident_store_path": tmp_path / "incidents.json",
        }
    )
    await agent.initialize()

    async def fake_query_metrics(service_name, metric_name, time_range):
        return [{"timestamp": datetime.utcnow().isoformat(), "metric": metric_name, "value": 42}]

    monkeypatch.setattr(agent, "_query_metrics", fake_query_metrics)

    history = await agent.process(
        {
            "action": "query_historical_metrics",
            "service_name": "api",
            "metric_name": "cpu_usage",
            "time_range": {"days": 1},
        }
    )
    assert history["values"]

    forecast = await agent.process({"action": "forecast_capacity", "service_name": "api"})
    assert "forecasts" in forecast


@pytest.mark.asyncio
async def test_system_health_anomaly_streaming_and_servicenow(monkeypatch, tmp_path):
    agent = SystemHealthAgent(
        config={
            "alert_store_path": tmp_path / "alerts.json",
            "incident_store_path": tmp_path / "incidents.json",
        }
    )
    await agent.initialize()

    metrics = [
        {"metric": "latency_ms", "value": 10, "timestamp": datetime.utcnow().isoformat()},
        {"metric": "latency_ms", "value": 11, "timestamp": datetime.utcnow().isoformat()},
        {"metric": "latency_ms", "value": 9, "timestamp": datetime.utcnow().isoformat()},
        {"metric": "latency_ms", "value": 10, "timestamp": datetime.utcnow().isoformat()},
        {"metric": "latency_ms", "value": 12, "timestamp": datetime.utcnow().isoformat()},
        {"metric": "latency_ms", "value": 1000, "timestamp": datetime.utcnow().isoformat()},
    ]

    async def fake_get_service_metrics(service_name, time_range):
        return metrics

    events = []
    incidents = []

    async def fake_emit_event_hub_event(payload):
        events.append(payload)

    async def fake_create_servicenow_incident(incident):
        incidents.append(incident)

    monkeypatch.setattr(agent, "_get_service_metrics", fake_get_service_metrics)
    monkeypatch.setattr(agent, "_emit_event_hub_event", fake_emit_event_hub_event)
    monkeypatch.setattr(agent, "_create_servicenow_incident", fake_create_servicenow_incident)

    response = await agent.process(
        {
            "action": "detect_anomalies",
            "service_name": "api",
            "time_range": {"days": 1},
        }
    )

    assert response["anomalies_detected"] > 0
    assert events
    assert incidents
