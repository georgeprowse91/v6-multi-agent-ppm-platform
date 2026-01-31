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
                "sources": [
                    {"url": "https://example.com/risk", "citation": "Supply chain warning"}
                ],
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


class _FakeKnowledgeBaseService:
    async def query_mitigations(self, risk):
        return [
            {"strategy": "Negotiate alternate suppliers", "source": "sharepoint"},
            {"strategy": "Increase buffer inventory", "source": "confluence"},
        ]


class _FakeMLService:
    async def predict_classification(self, payload):
        return {
            "status": "predicted",
            "result": {"probability": 4, "impact": 5, "severity_score": 20},
        }


class _FakeEventBus:
    def __init__(self):
        self.published = []

    async def publish(self, topic, payload):
        self.published.append((topic, payload))


class _FakeCognitiveSearch:
    def extract_risks(self, documents):
        return [
            {
                "title": "Scope creep risk",
                "description": "Scope creep detected in requirements document.",
                "category": "document",
                "source": "cognitive_search",
            }
        ]


@pytest.mark.asyncio
async def test_risk_management_predicts_with_ml(tmp_path):
    agent = RiskManagementAgent(
        config={"risk_store_path": tmp_path / "risk.json", "ml_service": _FakeMLService()}
    )
    await agent.initialize()

    created = await agent.process(
        {
            "action": "identify_risk",
            "tenant_id": "tenant-r",
            "risk": {
                "title": "Vendor delay",
                "description": "Supplier delays could impact schedule.",
                "category": "schedule",
                "probability": 2,
                "impact": 2,
            },
        }
    )

    assessed = await agent.process({"action": "assess_risk", "risk_id": created["risk_id"]})

    assert assessed["probability"] == 4
    assert assessed["impact"] == 5


@pytest.mark.asyncio
async def test_risk_management_mitigation_guidance_from_knowledge_base(tmp_path):
    agent = RiskManagementAgent(
        config={
            "risk_store_path": tmp_path / "risk.json",
            "knowledge_base_service": _FakeKnowledgeBaseService(),
        }
    )
    await agent.initialize()

    created = await agent.process(
        {
            "action": "identify_risk",
            "tenant_id": "tenant-r",
            "risk": {
                "title": "Skill shortage",
                "description": "Resource constraints may delay delivery.",
                "category": "resource",
            },
        }
    )

    plan = await agent.process(
        {
            "action": "create_mitigation_plan",
            "risk_id": created["risk_id"],
            "mitigation": {"strategy": "mitigate"},
        }
    )

    assert "Negotiate alternate suppliers" in plan["recommended_strategies"]


@pytest.mark.asyncio
async def test_risk_management_trigger_publishes_event(tmp_path):
    event_bus = _FakeEventBus()
    agent = RiskManagementAgent(
        config={"risk_store_path": tmp_path / "risk.json", "event_bus": event_bus}
    )
    await agent.initialize()

    created = await agent.process(
        {
            "action": "identify_risk",
            "tenant_id": "tenant-r",
            "risk": {
                "title": "Integration delay",
                "description": "Integration dependencies might slip.",
                "category": "schedule",
                "triggers": [{"threshold": 5, "current_value": 6}],
            },
        }
    )

    result = await agent.process({"action": "monitor_triggers", "risk_id": created["risk_id"]})

    assert result["risks_triggered"] == 1
    assert any(topic == "risk.triggered" for topic, _payload in event_bus.published)


@pytest.mark.asyncio
async def test_risk_management_extracts_risks_from_documents(tmp_path):
    agent = RiskManagementAgent(
        config={
            "risk_store_path": tmp_path / "risk.json",
            "cognitive_search_service": _FakeCognitiveSearch(),
        }
    )
    await agent.initialize()

    response = await agent.process(
        {
            "action": "identify_risk",
            "tenant_id": "tenant-r",
            "risk": {
                "title": "Requirements drift",
                "description": "Requirements are changing rapidly.",
                "category": "scope",
                "documents": [{"content": "Risk: scope creep likely."}],
            },
        }
    )

    assert response["extracted_risks"]
