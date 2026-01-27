import json

import pytest
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
