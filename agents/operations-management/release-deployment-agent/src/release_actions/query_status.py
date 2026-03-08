"""Action handlers: get_release_calendar, get_release_status, get_deployment_status, get_deployment_history."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from release_utils import matches_filters, matches_history_filters

if TYPE_CHECKING:
    from release_models import ReleaseAgentProtocol


async def get_release_calendar(
    agent: ReleaseAgentProtocol, filters: dict[str, Any]
) -> dict[str, Any]:
    """
    Get release calendar view.

    Returns scheduled releases.
    """
    agent.logger.info("Retrieving release calendar")

    # Filter releases
    filtered_releases = []
    for release_id, release in agent.releases.items():
        if await matches_filters(release, filters):
            filtered_releases.append(
                {
                    "release_id": release_id,
                    "name": release.get("name"),
                    "planned_date": release.get("planned_date"),
                    "actual_date": release.get("actual_date"),
                    "target_environment": release.get("target_environment"),
                    "status": release.get("status"),
                }
            )

    # Sort by planned date
    filtered_releases.sort(key=lambda x: x.get("planned_date", ""))

    return {
        "total_releases": len(filtered_releases),
        "releases": filtered_releases,
        "filters": filters,
    }


async def get_release_status(agent: ReleaseAgentProtocol, release_id: str) -> dict[str, Any]:
    """
    Get detailed release status.

    Returns comprehensive status information.
    """
    agent.logger.info("Getting release status: %s", release_id)

    release = agent.releases.get(release_id)
    if not release:
        raise ValueError(f"Release not found: {release_id}")

    # Find associated deployment plan
    deployment_plan = None
    for plan_id, plan in agent.deployment_plans.items():
        if plan.get("release_id") == release_id:
            deployment_plan = plan
            break

    return {
        "release_id": release_id,
        "name": release.get("name"),
        "status": release.get("status"),
        "planned_date": release.get("planned_date"),
        "actual_date": release.get("actual_date"),
        "target_environment": release.get("target_environment"),
        "deployment_plan": (deployment_plan.get("deployment_plan_id") if deployment_plan else None),
        "deployment_status": deployment_plan.get("status") if deployment_plan else None,
    }


async def get_deployment_status(
    agent: ReleaseAgentProtocol, deployment_plan_id: str
) -> dict[str, Any]:
    deployment_plan = agent.deployment_plans.get(deployment_plan_id)
    if not deployment_plan:
        raise ValueError(f"Deployment plan not found: {deployment_plan_id}")
    logs = agent.deployment_logs.get(deployment_plan_id, [])
    artifacts = agent.deployment_artifacts.get(deployment_plan_id, [])
    return {
        "deployment_plan_id": deployment_plan_id,
        "release_id": deployment_plan.get("release_id"),
        "environment": deployment_plan.get("environment"),
        "status": deployment_plan.get("status"),
        "started_at": deployment_plan.get("started_at"),
        "completed_at": deployment_plan.get("completed_at"),
        "rollback_executed": deployment_plan.get("rollback_executed", False),
        "logs": logs,
        "artifacts": artifacts,
    }


async def get_deployment_history(
    agent: ReleaseAgentProtocol,
    *,
    filters: dict[str, Any],
    limit: int,
) -> dict[str, Any]:
    history = [
        record
        for record in agent.deployment_history
        if await matches_history_filters(record, filters)
    ]
    history.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
    return {"history": history[:limit], "count": len(history), "filters": filters}
