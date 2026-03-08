"""Action handler: create_deployment_plan."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast

from release_utils import generate_deployment_plan_id

if TYPE_CHECKING:
    from release_models import ReleaseAgentProtocol


async def create_deployment_plan(
    agent: ReleaseAgentProtocol,
    release_id: str,
    plan_data: dict[str, Any],
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Create detailed deployment plan with workflow steps.

    Returns deployment plan ID and workflow.
    """
    agent.logger.info("Creating deployment plan for release: %s", release_id)

    release = agent.releases.get(release_id)
    if not release:
        raise ValueError(f"Release not found: {release_id}")

    # Generate deployment plan ID
    plan_id = await generate_deployment_plan_id()

    # Define deployment steps
    deployment_steps = await _define_deployment_steps(release, plan_data.get("custom_steps", []))

    # Define pre-deployment tasks
    pre_deployment = await _define_pre_deployment_tasks(release)

    # Define post-deployment verification
    post_deployment = await _define_post_deployment_verification(release)

    # Define rollback procedures
    rollback_steps = await _define_rollback_procedures(release)

    # Create deployment plan
    deployment_plan = {
        "deployment_plan_id": plan_id,
        "release_id": release_id,
        "environment": release.get("target_environment"),
        "strategy": plan_data.get("strategy") or release.get("deployment_strategy", "rolling"),
        "traffic_steps": plan_data.get("traffic_steps"),
        "pre_deployment_tasks": pre_deployment,
        "deployment_steps": deployment_steps,
        "post_deployment_verification": post_deployment,
        "rollback_procedures": rollback_steps,
        "estimated_duration_minutes": await _estimate_deployment_duration(deployment_steps),
        "responsible_owner": plan_data.get("owner"),
        "status": "Draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Store deployment plan
    agent.deployment_plans[plan_id] = deployment_plan
    agent.deployment_plan_store.upsert(tenant_id, plan_id, deployment_plan)

    # Persist to database
    await agent.db_service.store("deployment_plans", plan_id, deployment_plan)

    return {
        "deployment_plan_id": plan_id,
        "release_id": release_id,
        "environment": deployment_plan["environment"],
        "strategy": deployment_plan["strategy"],
        "total_steps": len(deployment_steps),
        "estimated_duration_minutes": deployment_plan["estimated_duration_minutes"],
        "pre_deployment_tasks": len(pre_deployment),
        "post_deployment_checks": len(post_deployment),
        "next_steps": "Review and execute deployment plan",
    }


# ---------------------------------------------------------------------------
# Step definition helpers (private to this module)
# ---------------------------------------------------------------------------


async def _define_deployment_steps(
    release: dict[str, Any], custom_steps: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Define deployment steps."""
    if custom_steps:
        return custom_steps
    return [
        {"step": 1, "action": "Backup database", "estimated_minutes": 15},
        {"step": 2, "action": "Stop application", "estimated_minutes": 5},
        {"step": 3, "action": "Deploy artifacts", "estimated_minutes": 20},
        {"step": 4, "action": "Run database migrations", "estimated_minutes": 10},
        {"step": 5, "action": "Start application", "estimated_minutes": 5},
        {"step": 6, "action": "Verify deployment", "estimated_minutes": 10},
    ]


async def _define_pre_deployment_tasks(release: dict[str, Any]) -> list[dict[str, Any]]:
    """Define pre-deployment tasks."""
    return [
        {"task": "Backup production database"},
        {"task": "Create configuration snapshot"},
        {"task": "Notify stakeholders"},
    ]


async def _define_post_deployment_verification(
    release: dict[str, Any],
) -> list[dict[str, Any]]:
    """Define post-deployment verification steps."""
    return [
        {"check": "Application health check"},
        {"check": "Database connectivity"},
        {"check": "API endpoints responding"},
        {"check": "Performance metrics within baseline"},
    ]


async def _define_rollback_procedures(release: dict[str, Any]) -> list[dict[str, Any]]:
    """Define rollback procedures."""
    return [
        {"step": 1, "action": "Stop current application"},
        {"step": 2, "action": "Restore previous artifacts"},
        {"step": 3, "action": "Rollback database"},
        {"step": 4, "action": "Start previous version"},
        {"step": 5, "action": "Verify rollback"},
    ]


async def _estimate_deployment_duration(deployment_steps: list[dict[str, Any]]) -> int:
    """Estimate total deployment duration."""
    total_minutes = sum(int(step.get("estimated_minutes", 5)) for step in deployment_steps)
    return cast(int, total_minutes)  # type: ignore
