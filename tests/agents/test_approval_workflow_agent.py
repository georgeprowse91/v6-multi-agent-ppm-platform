import pytest
from approval_workflow_agent import ApprovalWorkflowAgent


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
