"""Action handlers for quality plan management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from quality_models import build_quality_plan
from quality_utils import generate_plan_id

if TYPE_CHECKING:
    from quality_management_agent import QualityManagementAgent


async def create_quality_plan(
    agent: QualityManagementAgent,
    plan_data: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Create quality plan with objectives and metrics.

    Returns plan ID and objectives.
    """
    agent.logger.info("Creating quality plan for project: %s", plan_data.get("project_id"))

    plan_id = await generate_plan_id()
    recommended_metrics = await _recommend_quality_metrics(agent, plan_data)

    quality_plan = build_quality_plan(plan_id, plan_data, agent.quality_standards)
    # Override metrics with recommended if not specified
    quality_plan["metrics"] = plan_data.get("metrics", recommended_metrics)

    agent.quality_plans[plan_id] = quality_plan
    agent.quality_plan_store.upsert(tenant_id, plan_id, quality_plan)
    await agent._publish_quality_event(
        "quality.plan.created",
        payload={
            "plan_id": plan_id,
            "project_id": quality_plan.get("project_id"),
            "created_at": quality_plan.get("created_at"),
        },
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )

    await agent._store_record("quality_plans", plan_id, quality_plan)
    approval_response = await _request_quality_plan_approval(
        agent, plan_id, quality_plan, tenant_id=tenant_id, correlation_id=correlation_id
    )
    if approval_response:
        quality_plan = await _apply_quality_plan_approval(
            agent,
            quality_plan,
            approval_response,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )
        await agent._store_record("quality_plans", plan_id, quality_plan)

    return {
        "plan_id": plan_id,
        "project_id": quality_plan["project_id"],
        "objectives": quality_plan["objectives"],
        "metrics": quality_plan["metrics"],
        "recommended_metrics": recommended_metrics,
        "status": quality_plan["status"],
        "approval": approval_response,
        "next_steps": (
            "Await approval decision"
            if approval_response
            else "Review plan and submit for approval"
        ),
    }


async def approve_quality_plan(
    agent: QualityManagementAgent,
    plan_id: str | None,
    *,
    approver: str,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Approve a quality plan and publish an approval event."""
    if not plan_id:
        raise ValueError("plan_id is required for approval")
    plan = agent.quality_plans.get(plan_id)
    if not plan:
        stored_plan = agent.quality_plan_store.get(tenant_id, plan_id)
        if not stored_plan:
            raise ValueError(f"Quality plan not found: {plan_id}")
        plan = stored_plan
        agent.quality_plans[plan_id] = plan

    plan["status"] = "Approved"
    plan["approved_by"] = approver
    plan["approved_at"] = datetime.now(timezone.utc).isoformat()
    agent.quality_plan_store.upsert(tenant_id, plan_id, plan)

    await agent._publish_quality_event(
        "quality.plan.approved",
        payload={
            "plan_id": plan_id,
            "project_id": plan.get("project_id"),
            "approved_by": approver,
            "approved_at": plan.get("approved_at"),
        },
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )

    await agent._store_record("quality_plans", plan_id, plan)

    return {
        "plan_id": plan_id,
        "status": plan["status"],
        "approved_by": approver,
        "approved_at": plan.get("approved_at"),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _recommend_quality_metrics(
    agent: QualityManagementAgent, plan_data: dict[str, Any]
) -> list[dict[str, Any]]:
    """Recommend quality metrics based on project type."""
    baseline = [
        {
            "name": "defect_density",
            "threshold": agent.defect_density_threshold,
            "unit": "defects/kloc",
        },
        {"name": "test_coverage", "threshold": agent.min_test_coverage, "unit": "percentage"},
        {"name": "pass_rate", "threshold": 0.95, "unit": "percentage"},
        {"name": "mean_time_to_resolution", "threshold": 48, "unit": "hours"},
    ]
    project_type = str(plan_data.get("project_type", "")).lower()
    if project_type in {"compliance", "regulated"}:
        baseline.append({"name": "audit_score", "threshold": 0.9, "unit": "percentage"})
    return baseline


async def _request_quality_plan_approval(
    agent: QualityManagementAgent,
    plan_id: str,
    quality_plan: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any] | None:
    if not agent.approval_agent_enabled:
        return None
    if not agent.approval_agent:
        try:
            from approval_workflow_agent import ApprovalWorkflowAgent
        except ImportError:
            return None
        agent.approval_agent = ApprovalWorkflowAgent(config=agent.approval_agent_config)
    response = await agent.approval_agent.process(
        {
            "request_type": "quality_plan_approval",
            "request_id": plan_id,
            "requester": quality_plan.get("created_by", "unknown"),
            "details": {
                "project_id": quality_plan.get("project_id"),
                "objectives": quality_plan.get("objectives"),
                "metrics": quality_plan.get("metrics"),
            },
            "tenant_id": tenant_id,
            "correlation_id": correlation_id,
            "context": {"tenant_id": tenant_id, "correlation_id": correlation_id},
        }
    )
    await agent._publish_quality_event(
        "quality.plan.approval.requested",
        payload={"plan_id": plan_id, "approval": response},
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )
    return response


async def _apply_quality_plan_approval(
    agent: QualityManagementAgent,
    quality_plan: dict[str, Any],
    approval_response: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    status = approval_response.get("status", "pending")
    normalized = status.lower()
    if normalized in {"approved", "approve"}:
        quality_plan["status"] = "Approved"
    elif normalized in {"rejected", "denied"}:
        quality_plan["status"] = "Rejected"
    else:
        quality_plan["status"] = "Pending Approval"
    quality_plan["approval"] = approval_response
    agent.quality_plan_store.upsert(tenant_id, quality_plan["plan_id"], quality_plan)
    await agent._store_record("quality_plan_approvals", quality_plan["plan_id"], approval_response)
    if quality_plan["status"] == "Approved":
        await agent._publish_quality_event(
            "quality.plan.approved",
            payload={
                "plan_id": quality_plan.get("plan_id"),
                "project_id": quality_plan.get("project_id"),
                "approved_by": approval_response.get("approver", "workflow"),
                "approved_at": datetime.now(timezone.utc).isoformat(),
            },
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )
    return quality_plan
