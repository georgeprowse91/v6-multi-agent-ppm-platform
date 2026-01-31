import pytest
import risk_management_agent as risk_management_module
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


@pytest.mark.asyncio
async def test_risk_management_external_research_merges(tmp_path, monkeypatch):
    async def fake_search(_query: str, *, result_limit: int | None = None) -> list[str]:
        return ["Supply chain warning (https://example.com/risk)"]

    async def fake_summary(_snippets, **_kwargs):
        return "Supply chain disruption risk."

    async def fake_classify(self, _summary, _snippets, _categories, *, llm_client=None):
        return [
            {
                "title": "Supply chain disruption",
                "description": "Potential delays due to supplier issues.",
                "category": "schedule",
                "probability": 4,
                "impact": 4,
                "sources": [{"url": "https://example.com/risk", "citation": "Supply chain warning"}],
            }
        ]

    monkeypatch.setattr(risk_management_module, "search_web", fake_search)
    monkeypatch.setattr(risk_management_module, "summarize_snippets", fake_summary)
    monkeypatch.setattr(RiskManagementAgent, "_classify_external_risks", fake_classify)

    agent = RiskManagementAgent(
        config={
            "enable_external_risk_research": True,
            "risk_store_path": tmp_path / "risk.json",
        }
    )
    await agent.initialize()

    result = await agent.process(
        {
            "action": "research_risks",
            "tenant_id": "tenant-r",
            "project_id": "project-1",
            "domain": "manufacturing",
        }
    )

    assert result["used_external_research"] is True
    assert result["added_risks"]
