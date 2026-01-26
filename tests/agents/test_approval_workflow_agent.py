import json

import pytest
from approval_workflow_agent import ApprovalWorkflowAgent


@pytest.mark.asyncio
async def test_approval_workflow_persistence(tmp_path):
    storage_path = tmp_path / "approvals.json"
    notification_path = tmp_path / "notifications.json"
    agent = ApprovalWorkflowAgent(
        config={
            "storage_path": str(storage_path),
            "notification_store_path": str(notification_path),
        }
    )
    await agent.initialize()

    result = await agent.process(
        {
            "request_type": "budget_change",
            "request_id": "REQ-100",
            "requester": "user-1",
            "details": {"amount": 75000, "description": "Increase budget", "urgency": "high"},
        }
    )

    assert result["status"] == "pending"
    assert storage_path.exists()
    assert notification_path.exists()

    stored = json.loads(storage_path.read_text())
    notifications = json.loads(notification_path.read_text())

    assert result["approval_id"] in stored
    assert notifications[0]["approval_id"] == result["approval_id"]
