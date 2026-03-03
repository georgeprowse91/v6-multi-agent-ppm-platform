"""Action handler: rollback_deployment."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from release_utils import (
    build_rollback_plan,
    orchestrate_rollback,
    publish_event,
    restore_previous_release,
    write_rollback_script,
)

if TYPE_CHECKING:
    from release_models import ReleaseAgentProtocol


async def rollback_deployment(
    agent: ReleaseAgentProtocol, deployment_plan_id: str
) -> dict[str, Any]:
    """
    Execute rollback procedures.

    Returns rollback status.
    """
    agent.logger.info("Rolling back deployment: %s", deployment_plan_id)

    deployment_plan = agent.deployment_plans.get(deployment_plan_id)
    if not deployment_plan:
        raise ValueError(f"Deployment plan not found: {deployment_plan_id}")

    await publish_event(
        agent,
        "deployment.rollback.started",
        {
            "deployment_plan_id": deployment_plan_id,
            "release_id": deployment_plan.get("release_id"),
            "environment": deployment_plan.get("environment"),
            "strategy": deployment_plan.get("strategy"),
            "status": "In Progress",
        },
    )

    # Execute rollback steps
    rollback_steps = deployment_plan.get("rollback_procedures", [])
    rollback_results = await _execute_rollback_steps(
        agent, rollback_steps, deployment_plan=deployment_plan
    )

    # Update status
    deployment_plan["rollback_executed"] = True
    deployment_plan["rollback_at"] = datetime.now(timezone.utc).isoformat()
    deployment_plan["status"] = "Rolled Back"

    # Persist to database
    await agent.db_service.store("deployment_plans", deployment_plan_id, deployment_plan)

    await publish_event(
        agent,
        "deployment.rollback.completed",
        {
            "deployment_plan_id": deployment_plan_id,
            "release_id": deployment_plan.get("release_id"),
            "environment": deployment_plan.get("environment"),
            "strategy": deployment_plan.get("strategy"),
            "status": deployment_plan["status"],
            "rollback_executed": rollback_results.get("success", False),
            "rollback_details": rollback_results,
        },
    )

    return {
        "deployment_plan_id": deployment_plan_id,
        "rollback_status": "Success" if rollback_results.get("success") else "Failed",
        "rollback_results": rollback_results,
        "next_steps": "Investigate root cause and plan remediation",
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


async def _execute_rollback_steps(
    agent: ReleaseAgentProtocol,
    steps: list[dict[str, Any]],
    *,
    deployment_plan: dict[str, Any],
) -> dict[str, Any]:
    """Execute rollback steps."""
    rb_plan = await build_rollback_plan(agent, deployment_plan, steps)
    script_path = await write_rollback_script(agent, rb_plan)
    vcs_result = await restore_previous_release(agent, rb_plan)
    executed_steps = await orchestrate_rollback(rb_plan)
    success = executed_steps.get("success", False) and vcs_result.get("success", False)
    return {
        "success": success,
        "completed_steps": executed_steps.get("completed_steps", 0),
        "script_path": script_path,
        "version_control": vcs_result,
        "rollback_plan": rb_plan,
    }
