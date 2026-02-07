import asyncio

import pytest
from approval_workflow_agent import ApprovalWorkflowAgent
from integrations.services.integration import EventBusClient, EventEnvelope


@pytest.mark.asyncio
async def test_approval_workflow_persistence_and_delegation(tmp_path, monkeypatch):
    storage_path = tmp_path / "approvals.json"
    audit_events = []

    def capture_audit(event):
        audit_events.append(event)

    monkeypatch.setattr("approval_workflow_agent.emit_audit_event", capture_audit)

    agent = ApprovalWorkflowAgent(
        config={
            "approval_store_path": str(storage_path),
            "role_directory": {
                "project_manager": ["pm-1"],
                "sponsor": ["sponsor-1"],
                "finance_director": ["finance-1"],
            },
            "delegations": {"sponsor-1": "delegate-1"},
        }
    )
    await agent.initialize()

    result = await agent.process(
        {
            "request_type": "budget_change",
            "request_id": "REQ-100",
            "requester": "user-1",
            "details": {"amount": 75000, "description": "Increase budget", "urgency": "high"},
            "context": {"tenant_id": "tenant-alpha", "correlation_id": "corr-1"},
        }
    )

    assert result["status"] == "pending"
    assert storage_path.exists()
    assert "delegate-1" in result["approvers"]
    stored = storage_path.read_text()
    assert result["approval_id"] in stored
    assert any(event["action"] == "approval.created" for event in audit_events)

    decision_result = await agent.process(
        {
            "decision": "approved",
            "approval_id": result["approval_id"],
            "approver_id": "delegate-1",
            "comments": "approved",
            "context": {"tenant_id": "tenant-alpha", "correlation_id": "corr-2"},
        }
    )

    assert decision_result["status"] == "approved"
    assert any(event["action"] == "approval.decision" for event in audit_events)
    await agent.cleanup()


@pytest.mark.asyncio
async def test_approval_workflow_validation_rejects_invalid_type(tmp_path):
    agent = ApprovalWorkflowAgent(config={"approval_store_path": tmp_path / "approvals.json"})
    await agent.initialize()

    valid = await agent.validate_input(
        {
            "request_type": "invalid",
            "request_id": "REQ-200",
            "requester": "user-1",
            "details": {"amount": 10, "description": "bad"},
        }
    )

    assert valid is False
    await agent.cleanup()


@pytest.mark.asyncio
async def test_approval_workflow_validation_rejects_missing_fields(tmp_path):
    agent = ApprovalWorkflowAgent(config={"approval_store_path": tmp_path / "approvals.json"})
    await agent.initialize()

    valid = await agent.validate_input({"request_type": "budget_change"})

    assert valid is False
    await agent.cleanup()


@pytest.mark.asyncio
async def test_approval_workflow_decision_flow(tmp_path):
    agent = ApprovalWorkflowAgent(config={"approval_store_path": tmp_path / "approvals.json"})
    await agent.initialize()

    initial = await agent.process(
        {
            "request_type": "scope_change",
            "request_id": "REQ-201",
            "requester": "user-1",
            "details": {"description": "Scope update", "urgency": "low"},
        }
    )

    result = await agent.process(
        {
            "decision": "rejected",
            "approval_id": initial["approval_id"],
            "approver_id": "approver-1",
            "comments": "deny",
        }
    )

    assert result["status"] == "rejected"
    await agent.cleanup()


@pytest.mark.asyncio
async def test_approval_workflow_digest_notifications_and_templates(tmp_path, monkeypatch):
    storage_path = tmp_path / "approvals.json"
    sent_messages = []

    class FakeNotificationService:
        async def send_email(self, to, subject, body, metadata=None):
            sent_messages.append({"to": to, "subject": subject, "body": body})
            return {"status": "sent"}

        async def send_teams_message(self, team_id, channel_id, message, chat_id=None, user_id=None):
            sent_messages.append({"to": team_id or chat_id, "subject": "teams", "body": message})
            return {"status": "sent"}

        async def send_slack_message(self, destination, message):
            sent_messages.append({"to": destination, "subject": "slack", "body": message})
            return {"status": "sent"}

        async def send_push_notification(self, destination, message):
            sent_messages.append({"to": destination, "subject": "push", "body": message})
            return {"status": "sent"}

    agent = ApprovalWorkflowAgent(
        config={
            "approval_store_path": str(storage_path),
            "notification_routing": {
                "default": {
                    "delivery": "digest",
                    "digest_interval_minutes": 60,
                    "channels": {"email": {"address": "approver@example.com"}},
                }
            },
            "role_directory": {"project_manager": ["approver@example.com"]},
        }
    )
    await agent.initialize()
    agent.notification_service = FakeNotificationService()

    result = await agent.process(
        {
            "request_type": "resource_change",
            "request_id": "REQ-300",
            "requester": "user-1",
            "details": {"description": "Update resources", "urgency": "medium"},
            "context": {"tenant_id": "tenant-digest"},
        }
    )

    assert result["notifications_sent"] is True
    await agent.flush_digest_notifications("tenant-digest", "approver@example.com")
    assert any("pending approvals" in entry["subject"] for entry in sent_messages)
    await agent.cleanup()


@pytest.mark.asyncio
async def test_approval_workflow_event_subscription_records_decision(tmp_path):
    storage_path = tmp_path / "approvals.json"
    event_bus = EventBusClient()
    agent = ApprovalWorkflowAgent(
        config={
            "approval_store_path": str(storage_path),
            "role_directory": {"project_manager": ["pm@example.com"]},
            "event_bus_client": event_bus,
            "enable_event_publishing": True,
        }
    )
    await agent.initialize()

    result = await agent.process(
        {
            "request_type": "scope_change",
            "request_id": "REQ-400",
            "requester": "user-1",
            "details": {"description": "Scope update", "urgency": "low"},
            "context": {"tenant_id": "tenant-events"},
        }
    )

    envelope = EventEnvelope(
        event_type="approval.response",
        subject=result["approval_id"],
        data={
            "approval_id": result["approval_id"],
            "decision": "approved",
            "approver_id": "pm@example.com",
            "tenant_id": "tenant-events",
        },
        metadata={"tenant_id": "tenant-events"},
    )
    event_bus.publish_event(envelope)
    await asyncio.sleep(0)

    record = agent.approval_store.get("tenant-events", result["approval_id"])
    assert record
    assert record["status"] == "approved"
    await agent.cleanup()


@pytest.mark.asyncio
async def test_approval_workflow_subscription_management(tmp_path):
    storage_path = tmp_path / "approvals.json"
    agent = ApprovalWorkflowAgent(config={"approval_store_path": str(storage_path)})
    await agent.initialize()

    result = await agent.process(
        {
            "action": "subscribe_notifications",
            "tenant_id": "tenant-sub",
            "recipient": "user-9",
            "preferences": {"delivery": "digest", "channels": {"push": {"destinations": ["tok"]}}},
        }
    )
    assert result["status"] == "subscribed"

    stored = agent.notification_store.get_preferences("tenant-sub", "user-9")
    assert stored
    assert stored["delivery"] == "digest"
    await agent.cleanup()
