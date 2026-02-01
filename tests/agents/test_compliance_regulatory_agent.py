import compliance_regulatory_agent as compliance_regulatory_module
import pytest
from compliance_regulatory_agent import ComplianceRegulatoryAgent


class DummyEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    def subscribe(self, _topic: str, _handler) -> None:
        return None

    async def publish(self, topic: str, payload: dict) -> None:
        self.published.append((topic, payload))


class DummySecurityAgent:
    async def process(self, _payload: dict) -> dict:
        return {
            "security_scans": ["scan1"],
            "audit_logs": ["security-log"],
        }


@pytest.mark.asyncio
async def test_compliance_regulatory_persists_evidence_and_policy_check(tmp_path):
    agent = ComplianceRegulatoryAgent(
        config={
            "evidence_store_path": tmp_path / "evidence.json",
        }
    )
    await agent.initialize()

    regulation = await agent.process(
        {
            "action": "add_regulation",
            "regulation": {"name": "SOX", "description": "Controls"},
        }
    )
    control = await agent.process(
        {
            "action": "define_control",
            "control": {
                "description": "Access control",
                "regulation": regulation["regulation_id"],
                "owner": "compliance-owner",
            },
        }
    )
    mapping = await agent.process(
        {
            "action": "map_controls_to_project",
            "tenant_id": "tenant-c",
            "project_id": "project-1",
            "mapping": {},
        }
    )
    assert mapping["policy_decision"]["decision"] in {"allow", "deny"}

    evidence = await agent.process(
        {
            "action": "upload_evidence",
            "tenant_id": "tenant-c",
            "control_id": control["control_id"],
            "evidence": {
                "file_name": "access_log.csv",
                "file_url": "https://example.com/access_log.csv",
            },
        }
    )
    assert agent.evidence_store.get("tenant-c", evidence["evidence_id"])


@pytest.mark.asyncio
async def test_compliance_dashboard_success(tmp_path):
    agent = ComplianceRegulatoryAgent(
        config={
            "evidence_store_path": tmp_path / "evidence.json",
        }
    )
    await agent.initialize()

    response = await agent.process({"action": "get_compliance_dashboard", "tenant_id": "tenant-c"})

    assert "dashboard_generated_at" in response


@pytest.mark.asyncio
async def test_compliance_validation_rejects_invalid_action(tmp_path):
    agent = ComplianceRegulatoryAgent(
        config={
            "evidence_store_path": tmp_path / "evidence.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_compliance_validation_rejects_missing_control_fields(tmp_path):
    agent = ComplianceRegulatoryAgent(
        config={
            "evidence_store_path": tmp_path / "evidence.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input(
        {"action": "define_control", "control": {"description": "X"}}
    )

    assert valid is False


@pytest.mark.asyncio
async def test_compliance_external_monitoring_adds_updates(tmp_path, monkeypatch):
    async def fake_search(_query: str, *, result_limit: int | None = None) -> list[str]:
        return ["New privacy regulation (https://example.com/regulation)"]

    async def fake_summary(_snippets, **_kwargs):
        return "New privacy regulation for healthcare."

    async def fake_extract(self, _summary, _snippets, *, llm_client=None):
        return [
            {
                "regulation": "Health Data Privacy Act",
                "description": "New privacy rules for healthcare data.",
                "effective_date": "2025-01-01",
                "region": "US",
                "source_url": "https://example.com/regulation",
            }
        ]

    monkeypatch.setattr(compliance_regulatory_module, "search_web", fake_search)
    monkeypatch.setattr(compliance_regulatory_module, "summarize_snippets", fake_summary)
    monkeypatch.setattr(ComplianceRegulatoryAgent, "_extract_regulatory_updates", fake_extract)

    agent = ComplianceRegulatoryAgent(
        config={
            "enable_regulatory_monitoring": True,
            "evidence_store_path": tmp_path / "evidence.json",
        }
    )
    await agent.initialize()

    response = await agent.process(
        {
            "action": "monitor_regulatory_changes",
            "tenant_id": "tenant-c",
            "domain": "healthcare",
        }
    )

    assert response["external_monitoring"]["updates"]


@pytest.mark.asyncio
async def test_compliance_evidence_aggregation_includes_security(tmp_path):
    agent = ComplianceRegulatoryAgent(
        config={
            "seed_frameworks": True,
            "event_bus": DummyEventBus(),
            "agent_clients": {"security": DummySecurityAgent()},
            "evidence_store_path": tmp_path / "evidence.json",
        }
    )
    await agent.initialize()

    mapping = await agent.process(
        {
            "action": "map_controls_to_project",
            "tenant_id": "tenant-c",
            "project_id": "project-2",
            "mapping": {"industry": "technology", "geography": "global"},
        }
    )
    assert mapping["applicable_controls"] > 0

    assessment = await agent.process(
        {
            "action": "assess_compliance",
            "project_id": "project-2",
            "assessment": {"tenant_id": "tenant-c"},
        }
    )
    assert assessment["evidence_summary"]["security_scans"]


@pytest.mark.asyncio
async def test_compliance_event_handler_publishes_alerts(tmp_path):
    bus = DummyEventBus()
    agent = ComplianceRegulatoryAgent(
        config={
            "seed_frameworks": True,
            "event_bus": bus,
            "evidence_store_path": tmp_path / "evidence.json",
        }
    )
    await agent.initialize()

    await agent.process(
        {
            "action": "map_controls_to_project",
            "tenant_id": "tenant-c",
            "project_id": "project-3",
            "mapping": {"industry": "technology", "geography": "global"},
        }
    )
    await agent._handle_compliance_event(
        {"project_id": "project-3", "event_type": "deployment.completed"}
    )

    topics = [topic for topic, _payload in bus.published]
    assert "compliance.alert.raised" in topics


@pytest.mark.asyncio
async def test_compliance_certification_report_generation(tmp_path):
    agent = ComplianceRegulatoryAgent(
        config={
            "seed_frameworks": True,
            "event_bus": DummyEventBus(),
            "evidence_store_path": tmp_path / "evidence.json",
        }
    )
    await agent.initialize()

    report = await agent.process(
        {
            "action": "generate_compliance_report",
            "report_type": "soc2",
            "filters": {"project_id": "project-4", "industry": "technology"},
        }
    )

    assert report["report_type"] == "soc2"
