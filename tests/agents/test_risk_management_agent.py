import pytest
from risk_management_agent import RiskManagementAgent


@pytest.mark.asyncio
async def test_risk_management_persists_risk_register(tmp_path):
    agent = RiskManagementAgent(config={"risk_store_path": tmp_path / "risk.json"})
    await agent.initialize()

    response = await agent.process(
        {
            "action": "identify_risk",
            "tenant_id": "tenant-r",
            "risk": {
                "title": "Vendor delay",
                "description": "Supplier delays could impact schedule.",
                "category": "external",
                "probability": 3,
                "impact": 4,
                "owner": "risk-manager",
                "classification": "internal",
            },
        }
    )

    risk_id = response["risk_id"]
    assert agent.risk_store.get("tenant-r", risk_id)
    assert response["data_quality"]["is_valid"] is True


@pytest.mark.asyncio
async def test_risk_management_dashboard_success(tmp_path):
    agent = RiskManagementAgent(config={"risk_store_path": tmp_path / "risk.json"})
    await agent.initialize()

    response = await agent.process({"action": "get_risk_dashboard", "tenant_id": "tenant-r"})

    assert "risk_summary" in response


@pytest.mark.asyncio
async def test_risk_management_validation_rejects_invalid_action(tmp_path):
    agent = RiskManagementAgent(config={"risk_store_path": tmp_path / "risk.json"})
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_risk_management_validation_rejects_missing_fields(tmp_path):
    agent = RiskManagementAgent(config={"risk_store_path": tmp_path / "risk.json"})
    await agent.initialize()

    valid = await agent.validate_input({"action": "identify_risk", "risk": {"title": "X"}})

    assert valid is False
