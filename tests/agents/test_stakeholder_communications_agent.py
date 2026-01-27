import pytest
from stakeholder_communications_agent import StakeholderCommunicationsAgent


@pytest.mark.asyncio
async def test_stakeholder_persisted_and_consent_enforced(tmp_path):
    agent = StakeholderCommunicationsAgent(
        config={"stakeholder_store_path": tmp_path / "stakeholders.json"}
    )
    await agent.initialize()

    registration = await agent.process(
        {
            "action": "register_stakeholder",
            "tenant_id": "tenant-comms",
            "stakeholder": {
                "name": "Jamie Doe",
                "email": "jamie@example.com",
                "role": "Sponsor",
                "opt_out": True,
            },
        }
    )
    stakeholder_id = registration["stakeholder_id"]
    assert agent.stakeholder_store.get("tenant-comms", stakeholder_id)

    message = await agent.process(
        {
            "action": "generate_message",
            "tenant_id": "tenant-comms",
            "message": {
                "subject": "Status Update",
                "template": "Hello {name}",
                "data": {"name": "Jamie"},
                "stakeholder_ids": [stakeholder_id],
            },
        }
    )

    send = await agent.process(
        {
            "action": "send_message",
            "tenant_id": "tenant-comms",
            "message_id": message["message_id"],
        }
    )

    assert send["recipients"] == 1
    assert (
        agent.messages[message["message_id"]]["delivery_results"][0]["status"]
        == "skipped_no_consent"
    )


@pytest.mark.asyncio
async def test_stakeholder_dashboard_success(tmp_path):
    agent = StakeholderCommunicationsAgent(
        config={"stakeholder_store_path": tmp_path / "stakeholders.json"}
    )
    await agent.initialize()

    response = await agent.process(
        {"action": "get_stakeholder_dashboard", "tenant_id": "tenant-comms"}
    )

    assert "stakeholder_summary" in response


@pytest.mark.asyncio
async def test_stakeholder_validation_rejects_invalid_action(tmp_path):
    agent = StakeholderCommunicationsAgent(
        config={"stakeholder_store_path": tmp_path / "stakeholders.json"}
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_stakeholder_validation_rejects_missing_fields(tmp_path):
    agent = StakeholderCommunicationsAgent(
        config={"stakeholder_store_path": tmp_path / "stakeholders.json"}
    )
    await agent.initialize()

    valid = await agent.validate_input(
        {"action": "register_stakeholder", "stakeholder": {"name": "X"}}
    )

    assert valid is False
