"""Action handlers: get_stakeholder_dashboard, generate_communication_report"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from ..stakeholder_utils import (
    calculate_overall_engagement,
    calculate_overall_sentiment,
)

if TYPE_CHECKING:
    from ..stakeholder_communications_agent import StakeholderCommunicationsAgent


async def get_stakeholder_dashboard(
    agent: StakeholderCommunicationsAgent,
    project_id: str | None,
    filters: dict[str, Any],
) -> dict[str, Any]:
    """Get stakeholder dashboard data."""
    agent.logger.info("Getting stakeholder dashboard for project: %s", project_id)

    stakeholder_summary = await _get_stakeholder_summary(agent, project_id)
    engagement_overview = await _get_engagement_overview(agent, project_id)
    sentiment_trends = await _get_sentiment_trends(agent, project_id)
    upcoming_communications = await _get_upcoming_communications(agent, project_id)

    return {
        "project_id": project_id,
        "stakeholder_summary": stakeholder_summary,
        "engagement_overview": engagement_overview,
        "sentiment_trends": sentiment_trends,
        "upcoming_communications": upcoming_communications,
        "dashboard_generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def generate_communication_report(
    agent: StakeholderCommunicationsAgent,
    report_type: str,
    filters: dict[str, Any],
) -> dict[str, Any]:
    """Generate communication report."""
    agent.logger.info("Generating %s communication report", report_type)

    if report_type == "summary":
        return await _generate_summary_report(filters)
    elif report_type == "engagement":
        return await _generate_engagement_report(filters)
    elif report_type == "sentiment":
        return await _generate_sentiment_report(filters)
    else:
        raise ValueError(f"Unknown report type: {report_type}")


# ---------------------------------------------------------------------------
# Dashboard sub-helpers
# ---------------------------------------------------------------------------


async def _get_stakeholder_summary(
    agent: StakeholderCommunicationsAgent, project_id: str | None
) -> dict[str, Any]:
    """Get stakeholder summary."""
    return {
        "total_stakeholders": len(agent.stakeholder_register),
        "by_engagement_level": {"high": 0, "medium": 0, "low": 0},
    }


async def _get_engagement_overview(
    agent: StakeholderCommunicationsAgent, project_id: str | None
) -> dict[str, Any]:
    """Get engagement overview."""
    return await calculate_overall_engagement(agent)


async def _get_sentiment_trends(
    agent: StakeholderCommunicationsAgent, project_id: str | None
) -> dict[str, Any]:
    """Get sentiment trends."""
    return await calculate_overall_sentiment(agent)


async def _get_upcoming_communications(
    agent: StakeholderCommunicationsAgent, project_id: str | None
) -> list[dict[str, Any]]:
    """Get upcoming communications."""
    upcoming = []
    for message_id, message in agent.messages.items():
        if message.get("status") == "Draft" and message.get("scheduled_send"):
            upcoming.append(
                {
                    "message_id": message_id,
                    "subject": message.get("subject"),
                    "scheduled_send": message.get("scheduled_send"),
                }
            )
    return upcoming[:10]


async def _generate_summary_report(filters: dict[str, Any]) -> dict[str, Any]:
    """Generate summary communication report."""
    return {
        "report_type": "summary",
        "data": {},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def _generate_engagement_report(filters: dict[str, Any]) -> dict[str, Any]:
    """Generate engagement report."""
    return {
        "report_type": "engagement",
        "data": {},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def _generate_sentiment_report(filters: dict[str, Any]) -> dict[str, Any]:
    """Generate sentiment report."""
    return {
        "report_type": "sentiment",
        "data": {},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
