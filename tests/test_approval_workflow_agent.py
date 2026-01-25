"""
Tests for ApprovalWorkflowAgent input validation and lifecycle behavior.
"""

import pytest

from approval_workflow_agent import ApprovalWorkflowAgent


@pytest.mark.asyncio
async def test_approval_workflow_validation_rejects_missing_fields():
    """ApprovalWorkflowAgent should reject requests missing required fields."""
    agent = ApprovalWorkflowAgent()

    result = await agent.execute({"request_type": "budget_change"})

    assert result["success"] is False
    assert "validation" in result["error"].lower()


@pytest.mark.asyncio
async def test_approval_workflow_validation_rejects_invalid_type():
    """ApprovalWorkflowAgent should reject invalid request types."""
    agent = ApprovalWorkflowAgent()

    result = await agent.execute(
        {
            "request_type": "unknown_type",
            "request_id": "req-1",
            "requester": "user-1",
            "details": {"amount": 1000, "description": "test", "justification": "test"},
        }
    )

    assert result["success"] is False
    assert "validation" in result["error"].lower()


@pytest.mark.asyncio
async def test_approval_workflow_validation_accepts_valid_request():
    """ApprovalWorkflowAgent should accept a valid approval request."""
    agent = ApprovalWorkflowAgent()

    result = await agent.execute(
        {
            "request_type": "budget_change",
            "request_id": "req-123",
            "requester": "user-1",
            "details": {
                "amount": 1000,
                "description": "Increase budget for Phase 2",
                "justification": "Scope expansion",
                "urgency": "medium",
            },
        }
    )

    assert result["success"] is True
