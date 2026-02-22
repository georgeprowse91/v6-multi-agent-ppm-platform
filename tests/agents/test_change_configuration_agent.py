import pytest
from change_configuration_agent import ChangeConfigurationAgent, ImpactTrainingSample


class ApprovalMock:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    async def process(self, input_data: dict) -> dict:
        self.requests.append(input_data)
        return {"approval_id": "appr-change", "status": "pending"}


class EventPublisherMock:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def publish_event(self, topic: str, payload: dict) -> None:
        self.events.append({"topic": topic, "payload": payload})


@pytest.mark.asyncio
async def test_change_configuration_persists_and_requests_approval(tmp_path):
    approval_mock = ApprovalMock()
    agent = ChangeConfigurationAgent(
        config={
            "approval_agent": approval_mock,
            "change_store_path": tmp_path / "changes.json",
            "cmdb_store_path": tmp_path / "cmdb.json",
        }
    )
    await agent.initialize()

    change_response = await agent.process(
        {
            "action": "submit_change_request",
            "tenant_id": "tenant-chg",
            "change": {
                "title": "Upgrade database",
                "description": "Apply security patches",
                "requester": "ops",
                "priority": "high",
            },
        }
    )
    assert change_response["approval_required"] is True
    assert approval_mock.requests
    assert agent.change_store.get("tenant-chg", change_response["change_id"])

    ci_response = await agent.process(
        {
            "action": "register_ci",
            "tenant_id": "tenant-chg",
            "ci": {"name": "db-cluster", "type": "software", "owner": "ops"},
        }
    )
    assert agent.cmdb_store.get("tenant-chg", ci_response["ci_id"])


@pytest.mark.asyncio
async def test_change_configuration_dashboard(tmp_path):
    agent = ChangeConfigurationAgent(
        config={
            "change_store_path": tmp_path / "changes.json",
            "cmdb_store_path": tmp_path / "cmdb.json",
        }
    )
    await agent.initialize()

    response = await agent.process({"action": "get_change_dashboard", "tenant_id": "tenant-chg"})

    assert "open_changes" in response


@pytest.mark.asyncio
async def test_change_configuration_validation_rejects_invalid_action(tmp_path):
    agent = ChangeConfigurationAgent(
        config={
            "change_store_path": tmp_path / "changes.json",
            "cmdb_store_path": tmp_path / "cmdb.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_change_configuration_validation_rejects_missing_fields(tmp_path):
    agent = ChangeConfigurationAgent(
        config={
            "change_store_path": tmp_path / "changes.json",
            "cmdb_store_path": tmp_path / "cmdb.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input(
        {"action": "submit_change_request", "change": {"title": "X"}}
    )

    assert valid is False


@pytest.mark.asyncio
async def test_change_configuration_predicts_impact(tmp_path):
    agent = ChangeConfigurationAgent(
        config={
            "change_store_path": tmp_path / "changes.json",
            "cmdb_store_path": tmp_path / "cmdb.json",
            "impact_model_samples": [
                ImpactTrainingSample(1.0, 0.0, 1, "low", 0.9),
            ],
        }
    )
    await agent.initialize()

    response = await agent.process(
        {
            "action": "predict_impact",
            "change": {
                "complexity": 2,
                "historical_failure_rate": 0.1,
                "affected_services": 2,
                "risk_category": "low",
            },
        }
    )

    assert response["prediction"]["success_probability"] == 0.75


@pytest.mark.asyncio
async def test_change_configuration_graph_traversal(tmp_path):
    agent = ChangeConfigurationAgent(
        config={
            "change_store_path": tmp_path / "changes.json",
            "cmdb_store_path": tmp_path / "cmdb.json",
        }
    )
    await agent.initialize()

    ci_b = await agent.process(
        {"action": "register_ci", "tenant_id": "tenant-chg", "ci": {"name": "db", "type": "db"}}
    )
    ci_a = await agent.process(
        {
            "action": "register_ci",
            "tenant_id": "tenant-chg",
            "ci": {
                "name": "api",
                "type": "service",
                "relationships": [
                    {"target_ci_id": ci_b["ci_id"], "relationship_type": "depends_on"}
                ],
            },
        }
    )

    impacted = await agent._identify_impacted_cis({"ci_ids": [ci_a["ci_id"]]})

    assert ci_b["ci_id"] in impacted


@pytest.mark.asyncio
async def test_change_configuration_publishes_events(tmp_path):
    publisher = EventPublisherMock()
    agent = ChangeConfigurationAgent(
        config={
            "event_publisher": publisher,
            "change_store_path": tmp_path / "changes.json",
            "cmdb_store_path": tmp_path / "cmdb.json",
        }
    )
    await agent.initialize()

    response = await agent.process(
        {
            "action": "submit_change_request",
            "tenant_id": "tenant-chg",
            "change": {
                "title": "Update firewall rules",
                "description": "Apply approved network changes",
                "requester": "secops",
                "priority": "medium",
            },
        }
    )

    assert response["change_id"]
    assert publisher.events
