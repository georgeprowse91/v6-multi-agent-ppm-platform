"""Action handler: schedule_deployment_window."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from release_utils import (
    analyze_usage_patterns,
    detect_scheduling_conflicts,
    optimize_deployment_windows,
)

if TYPE_CHECKING:
    from release_models import ReleaseAgentProtocol


async def schedule_deployment_window(
    agent: ReleaseAgentProtocol,
    release_id: str,
    preferred_window: dict[str, Any],
) -> dict[str, Any]:
    """
    Schedule optimal deployment window.

    Returns scheduled window and conflicts.
    """
    agent.logger.info("Scheduling deployment window for release: %s", release_id)

    release = agent.releases.get(release_id)
    if not release:
        raise ValueError(f"Release not found: {release_id}")

    optimal_window = None
    usage_patterns = await analyze_usage_patterns(agent, release.get("target_environment"))

    if agent.schedule_agent and agent.schedule_agent_action:
        response = await agent.schedule_agent.process(
            {
                "action": agent.schedule_agent_action,
                "release_id": release_id,
                "preferred_window": preferred_window,
                "environment": release.get("target_environment"),
            }
        )
        optimal_window = response.get("scheduled_window") or response.get("window")

    if not optimal_window:
        optimal_window = await _find_optimal_deployment_window(
            agent, preferred_window, usage_patterns, release.get("target_environment")
        )

    # Check for conflicts
    start_time = optimal_window.get("start_time")
    target_env = release.get("target_environment")
    assert isinstance(start_time, str), "start_time must be a string"
    assert isinstance(target_env, str), "target_environment must be a string"
    conflicts = await detect_scheduling_conflicts(agent, start_time, target_env)

    return {
        "release_id": release_id,
        "scheduled_window": optimal_window,
        "conflicts": conflicts,
        "usage_impact": await _calculate_usage_impact(optimal_window, usage_patterns),
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


async def _find_optimal_deployment_window(
    agent: ReleaseAgentProtocol,
    preferred_window: dict[str, Any],
    usage_patterns: dict[str, Any],
    environment: str,
) -> dict[str, Any]:
    """Find optimal deployment window."""
    start_time_str = preferred_window.get("start_time")
    assert isinstance(start_time_str, str), "start_time must be a string"
    windows = await optimize_deployment_windows(
        agent,
        planned_date=start_time_str,
        environment=environment,
        preferred_window=preferred_window,
    )
    if windows:
        return windows[0]
    return {
        "start_time": start_time_str,
        "duration_hours": agent.deployment_window_hours,
        "end_time": (
            datetime.fromisoformat(start_time_str)
            + timedelta(hours=agent.deployment_window_hours)
        ).isoformat(),
    }


async def _calculate_usage_impact(
    window: dict[str, Any], usage_patterns: dict[str, Any]
) -> str:
    """Calculate usage impact."""
    start_time = window.get("start_time")
    if not isinstance(start_time, str):
        return "Unknown impact"
    hour = datetime.fromisoformat(start_time).hour
    if hour in usage_patterns.get("low_usage_hours", []):
        return "Low impact - deployment during low usage period"
    return "Moderate impact - deployment overlaps with typical usage window"
