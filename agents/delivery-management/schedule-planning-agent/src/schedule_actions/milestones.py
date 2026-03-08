"""Action handler for track_milestones."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from schedule_planning_agent import SchedulePlanningAgent


async def track_milestones(agent: SchedulePlanningAgent, schedule_id: str) -> dict[str, Any]:
    """
    Track milestones and upcoming deadlines.

    Returns milestone status and alerts.
    """
    agent.logger.info("Tracking milestones for schedule: %s", schedule_id)

    milestones = agent.milestones.get(schedule_id, [])

    # Get current date
    current_date = datetime.now(timezone.utc)

    # Categorize milestones
    upcoming_milestones = []
    past_due_milestones = []
    completed_milestones = []

    for milestone in milestones:
        milestone_date = datetime.fromisoformat(milestone.get("date"))
        status = milestone.get("status", "pending")

        if status == "completed":
            completed_milestones.append(milestone)
        elif milestone_date < current_date:
            past_due_milestones.append(milestone)
        else:
            days_until = (milestone_date - current_date).days
            if days_until <= 30:  # Upcoming within 30 days
                milestone["days_until"] = days_until
                upcoming_milestones.append(milestone)

    return {
        "schedule_id": schedule_id,
        "total_milestones": len(milestones),
        "upcoming_milestones": upcoming_milestones,
        "past_due_milestones": past_due_milestones,
        "completed_milestones": completed_milestones,
        "completion_rate": len(completed_milestones) / len(milestones) if milestones else 0,
    }
