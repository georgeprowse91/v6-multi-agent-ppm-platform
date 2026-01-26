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
