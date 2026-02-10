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


@pytest.mark.asyncio
async def test_dynamic_escalation_uses_high_risk_and_criticality_thresholds(tmp_path):
    """High-risk + critical requests should use the shortest configured escalation timeout."""
    agent = ApprovalWorkflowAgent(
        config={
            "approval_store_path": str(tmp_path / "approvals.json"),
            "role_directory": {"project_manager": ["pm-1"], "finance_director": ["fd-1"]},
            "approval_policies_path": str(tmp_path / "approval_policies.yaml"),
        }
    )
    (tmp_path / "approval_policies.yaml").write_text(
        """
escalation_timeout_hours: 48
risk_thresholds:
  high: 12
  medium: 24
  low: 48
criticality_levels:
  critical: 6
  high: 12
  normal: 24
  low: 48
""".strip()
    )
    await agent.initialize()

    result = await agent.process(
        {
            "request_type": "budget_change",
            "request_id": "req-risk-high",
            "requester": "user-1",
            "details": {
                "amount": 250000,
                "description": "Critical security remediation",
                "urgency": "high",
                "project_type": "security",
                "strategic_importance": "critical",
            },
            "context": {"tenant_id": "tenant-1"},
        }
    )

    assert result["metadata"]["risk_score"] == "high"
    assert result["metadata"]["criticality_level"] == "critical"
    assert result["metadata"]["escalation_timeout_hours"] == 6
    assert agent.escalation_timers[result["approval_id"]]["timeout_hours"] == 6
    await agent.cleanup()


@pytest.mark.asyncio
async def test_dynamic_escalation_uses_low_risk_defaults(tmp_path):
    """Low-risk + low-criticality requests should use the configured low timeout."""
    agent = ApprovalWorkflowAgent(
        config={
            "approval_store_path": str(tmp_path / "approvals.json"),
            "role_directory": {"project_manager": ["pm-1"]},
            "approval_policies_path": str(tmp_path / "approval_policies.yaml"),
        }
    )
    (tmp_path / "approval_policies.yaml").write_text(
        """
escalation_timeout_hours: 72
risk_thresholds:
  high: 10
  medium: 20
  low: 36
criticality_levels:
  critical: 8
  high: 18
  normal: 30
  low: 42
""".strip()
    )
    await agent.initialize()

    result = await agent.process(
        {
            "request_type": "resource_change",
            "request_id": "req-risk-low",
            "requester": "user-2",
            "details": {
                "amount": 500,
                "description": "Minor reallocation",
                "urgency": "low",
                "strategic_importance": "low",
            },
            "context": {"tenant_id": "tenant-2"},
        }
    )

    assert result["metadata"]["risk_score"] == "low"
    assert result["metadata"]["criticality_level"] == "normal"
    assert result["metadata"]["escalation_timeout_hours"] == 30
    assert agent.escalation_timers[result["approval_id"]]["timeout_hours"] == 30
    await agent.cleanup()
