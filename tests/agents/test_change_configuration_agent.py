import pytest
from change_configuration_agent import ChangeConfigurationAgent


class ApprovalStub:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    async def process(self, input_data: dict) -> dict:
        self.requests.append(input_data)
        return {"approval_id": "appr-change", "status": "pending"}


@pytest.mark.asyncio
async def test_change_configuration_persists_and_requests_approval(tmp_path):
    approval_stub = ApprovalStub()
    agent = ChangeConfigurationAgent(
        config={
            "approval_agent": approval_stub,
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
    assert approval_stub.requests
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
