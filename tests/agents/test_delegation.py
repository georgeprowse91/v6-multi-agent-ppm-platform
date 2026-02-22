import pytest
from approval_workflow_agent import ApprovalWorkflowAgent


@pytest.mark.asyncio
async def test_delegated_approver_receives_notification_and_recorded(tmp_path):
    storage_path = tmp_path / "approvals.json"
    now_window_start = "2024-01-01T00:00:00+00:00"
    now_window_end = "2099-12-31T23:59:59+00:00"

    agent = ApprovalWorkflowAgent(
        config={
            "approval_store_path": str(storage_path),
            "role_directory": {"project_manager": ["pm-1"], "sponsor": ["sponsor-1"]},
            "delegations": {
                "sponsor-1": {
                    "delegate": "delegate-1",
                    "start": now_window_start,
                    "end": now_window_end,
                }
            },
        }
    )
    await agent.initialize()

    result = await agent.process(
        {
            "request_type": "budget_change",
            "request_id": "REQ-DELEGATE-1",
            "requester": "requester-1",
            "details": {"amount": 20000, "description": "Delegated approval", "urgency": "medium"},
            "context": {"tenant_id": "tenant-delegation"},
        }
    )

    assert result["status"] == "pending"
    assert "delegate-1" in result["approvers"]

    record = agent.approval_store.get("tenant-delegation", result["approval_id"])
    assert record is not None
    delegations = record["details"]["chain"]["delegations"]
    assert delegations
    assert delegations[0]["delegator"] == "sponsor-1"
    assert delegations[0]["delegate"] == "delegate-1"

    notifications = record["details"]["notifications"]
    delegated_notification = next(
        item for item in notifications if item["assigned_approver"] == "delegate-1"
    )
    assert delegated_notification["to"] == "delegate-1"
    assert "on behalf of sponsor-1" in delegated_notification["body"]

    await agent.cleanup()


@pytest.mark.asyncio
async def test_delegate_direct_notification_flag_can_route_to_delegator(tmp_path):
    storage_path = tmp_path / "approvals.json"

    agent = ApprovalWorkflowAgent(
        config={
            "approval_store_path": str(storage_path),
            "role_directory": {"project_manager": ["pm-1"], "sponsor": ["sponsor-1"]},
            "delegations": {
                "sponsor-1": {
                    "delegate": "delegate-1",
                    "start": "2024-01-01T00:00:00+00:00",
                    "end": "2099-12-31T23:59:59+00:00",
                }
            },
        }
    )
    await agent.initialize()
    await agent.process(
        {
            "action": "subscribe_notifications",
            "tenant_id": "tenant-delegation",
            "recipient": "delegate-1",
            "preferences": {"notify_delegate_directly": False},
        }
    )

    result = await agent.process(
        {
            "request_type": "budget_change",
            "request_id": "REQ-DELEGATE-2",
            "requester": "requester-1",
            "details": {"amount": 25000, "description": "Delegated route", "urgency": "medium"},
            "context": {"tenant_id": "tenant-delegation"},
        }
    )

    record = agent.approval_store.get("tenant-delegation", result["approval_id"])
    assert record is not None
    notifications = record["details"]["notifications"]
    delegated_notification = next(
        item for item in notifications if item["assigned_approver"] == "delegate-1"
    )
    assert delegated_notification["to"] == "sponsor-1"

    await agent.cleanup()
