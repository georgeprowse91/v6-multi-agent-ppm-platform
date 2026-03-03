"""Action handler: plan_release."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from release_utils import (
    check_environment_availability,
    detect_scheduling_conflicts,
    generate_release_id,
    publish_event,
    suggest_alternative_windows,
)

if TYPE_CHECKING:
    from release_models import ReleaseAgentProtocol


async def plan_release(
    agent: ReleaseAgentProtocol,
    release_data: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """
    Plan a new release and add to calendar.

    Returns release ID and schedule.
    """
    agent.logger.info("Planning release: %s", release_data.get("name"))

    # Pre-flight quality gate check
    if agent.quality_agent:
        await agent.quality_agent.process(
            {"action": "pre_release_quality_check", "release_name": release_data.get("name")}
        )

    # Generate release ID
    release_id = await generate_release_id()

    target_environment = release_data.get("target_environment")
    planned_date = release_data.get("planned_date")
    assert isinstance(target_environment, str), "target_environment must be a string"
    assert isinstance(planned_date, str), "planned_date must be a string"

    # Check for environment availability
    env_availability = await check_environment_availability(
        agent, target_environment, planned_date, release_id
    )

    # Detect scheduling conflicts
    conflicts = await detect_scheduling_conflicts(agent, planned_date, target_environment)

    # Suggest alternative windows if conflicts exist
    alternative_windows: list[dict[str, Any]] = []
    if conflicts:
        alternative_windows = await suggest_alternative_windows(
            agent, planned_date, target_environment
        )

    approval_required = target_environment in agent.approval_environments
    approval_payload = None
    if approval_required:
        if agent.approval_agent:
            approval_payload = await agent.approval_agent.process(
                {
                    "request_type": "phase_gate",
                    "request_id": release_id,
                    "requester": release_data.get("requester", actor_id),
                    "details": {
                        "description": release_data.get("description"),
                        "environment": target_environment,
                        "planned_date": planned_date,
                        "urgency": release_data.get("urgency", "medium"),
                    },
                    "tenant_id": tenant_id,
                    "correlation_id": correlation_id,
                }
            )

    # Create release record
    release = {
        "release_id": release_id,
        "name": release_data.get("name"),
        "description": release_data.get("description"),
        "target_environment": release_data.get("target_environment"),
        "planned_date": release_data.get("planned_date"),
        "actual_date": None,
        "project_ids": release_data.get("project_ids", []),
        "change_requests": release_data.get("change_requests", []),
        "status": "Planned",
        "approval_required": approval_required,
        "approval": approval_payload,
        "approval_status": (
            approval_payload.get("status")
            if approval_payload
            else ("not_required" if not approval_required else "not_configured")
        ),
        "environment_available": env_availability,
        "conflicts": conflicts,
        "alternative_windows": alternative_windows,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": release_data.get("requester", "unknown"),
    }

    # Store release
    agent.releases[release_id] = release
    agent.release_store.upsert(tenant_id, release_id, release)

    # Persist to database
    await agent.db_service.store("releases", release_id, release)

    calendar_event = None
    if agent.calendar_service:
        calendar_event = agent.calendar_service.create_event(
            {
                "title": f"Release: {release.get('name')}",
                "summary": release.get("name"),
                "scheduled_time": release.get("planned_date"),
                "description": release.get("description"),
            }
        )
        release["calendar_event"] = calendar_event

    await publish_event(
        agent,
        "deployment.release_planned",
        {
            "release_id": release_id,
            "name": release["name"],
            "planned_date": release["planned_date"],
            "target_environment": release["target_environment"],
            "tenant_id": tenant_id,
        },
    )

    return {
        "release_id": release_id,
        "name": release["name"],
        "planned_date": release["planned_date"],
        "target_environment": release["target_environment"],
        "status": "planned",
        "environment_available": env_availability,
        "conflicts": conflicts,
        "alternative_windows": alternative_windows,
        "approval_required": approval_required,
        "approval": approval_payload,
        "calendar_event": calendar_event,
        "next_steps": "Create deployment plan and assess readiness",
    }
