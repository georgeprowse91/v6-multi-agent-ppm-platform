"""Action handler for sprint_planning."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from schedule_planning_agent import SchedulePlanningAgent


async def sprint_planning(
    agent: SchedulePlanningAgent, project_id: str, sprint_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Perform sprint planning for Adaptive projects.

    Returns sprint backlog and capacity planning.
    """
    agent.logger.info("Sprint planning for project: %s", project_id)

    # Get team velocity and capacity
    team_velocity = sprint_data.get("team_velocity", 0)
    team_capacity = sprint_data.get("team_capacity", 0)
    backlog_items = sprint_data.get("backlog_items", [])

    # Recommend sprint backlog based on capacity
    recommended_items = await recommend_sprint_backlog(backlog_items, team_velocity, team_capacity)

    # Calculate story points for sprint
    total_story_points = sum(item.get("story_points", 0) for item in recommended_items)

    # Generate burndown forecast
    burndown_forecast = await generate_burndown_forecast(
        total_story_points, sprint_data.get("sprint_duration_days", 10)
    )

    return {
        "project_id": project_id,
        "sprint_backlog": recommended_items,
        "total_story_points": total_story_points,
        "team_velocity": team_velocity,
        "team_capacity": team_capacity,
        "capacity_utilization": total_story_points / team_capacity if team_capacity > 0 else 0,
        "burndown_forecast": burndown_forecast,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def recommend_sprint_backlog(
    backlog_items: list[dict[str, Any]], team_velocity: float, team_capacity: float
) -> list[dict[str, Any]]:
    """Recommend sprint backlog items."""
    # Sort by priority and select items that fit capacity
    sorted_items = sorted(backlog_items, key=lambda x: x.get("priority", 0), reverse=True)

    selected = []
    total_points = 0

    for item in sorted_items:
        points = item.get("story_points", 0)
        if total_points + points <= team_capacity:
            selected.append(item)
            total_points += points

    return selected


async def generate_burndown_forecast(
    total_story_points: float, sprint_duration_days: int
) -> list[dict[str, Any]]:
    """Generate burndown forecast."""
    burndown = []
    daily_velocity = total_story_points / sprint_duration_days if sprint_duration_days > 0 else 0

    for day in range(sprint_duration_days + 1):
        remaining = max(0, total_story_points - (daily_velocity * day))
        burndown.append({"day": day, "remaining_points": remaining})

    return burndown
