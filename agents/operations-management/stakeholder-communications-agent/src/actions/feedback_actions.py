"""Action handlers: collect_feedback, analyze_sentiment"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from ..stakeholder_utils import (
    calculate_overall_sentiment,
    calculate_sentiment_trend,
    generate_feedback_id,
    publish_event,
    record_communication_history,
)

if TYPE_CHECKING:
    from ..stakeholder_communications_agent import StakeholderCommunicationsAgent


async def collect_feedback(
    agent: StakeholderCommunicationsAgent,
    feedback_data: dict[str, Any],
) -> dict[str, Any]:
    """Collect stakeholder feedback."""
    agent.logger.info("Collecting feedback from: %s", feedback_data.get("stakeholder_id"))

    feedback_id = await generate_feedback_id()

    sentiment = await agent._analyze_text_sentiment(feedback_data.get("comments", ""))

    feedback_record = {
        "feedback_id": feedback_id,
        "stakeholder_id": feedback_data.get("stakeholder_id"),
        "project_id": feedback_data.get("project_id"),
        "message_id": feedback_data.get("message_id"),
        "survey_response": feedback_data.get("survey_response", {}),
        "comments": feedback_data.get("comments"),
        "rating": feedback_data.get("rating"),
        "sentiment": sentiment,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }

    if feedback_data.get("stakeholder_id") not in agent.feedback:
        agent.feedback[feedback_data.get("stakeholder_id")] = []  # type: ignore

    agent.feedback[feedback_data.get("stakeholder_id")].append(feedback_record)  # type: ignore

    stakeholder = agent.stakeholder_register.get(feedback_data.get("stakeholder_id"))  # type: ignore
    if stakeholder:
        stakeholder["sentiment_score"] = sentiment.get("score", 0)
        stakeholder["last_feedback_date"] = datetime.now(timezone.utc).isoformat()
        agent.stakeholder_store.upsert(
            feedback_data.get("tenant_id", "default"),
            stakeholder.get("stakeholder_id"),
            stakeholder.copy(),
        )

    stakeholder_id = feedback_data.get("stakeholder_id")
    if stakeholder_id in agent.engagement_metrics:
        agent.engagement_metrics[stakeholder_id]["responses_received"] += 1

    record_communication_history(
        agent,
        {
            "stakeholder_id": feedback_data.get("stakeholder_id"),
            "channel": "feedback",
            "subject": "Stakeholder feedback",
            "status": "received",
            "content": feedback_data.get("comments"),
            "metadata": {"feedback_id": feedback_id, "sentiment": sentiment},
        },
    )
    publish_event(
        agent,
        "stakeholder.feedback.received",
        {
            "feedback_id": feedback_id,
            "stakeholder_id": feedback_data.get("stakeholder_id"),
            "sentiment": sentiment,
        },
    )

    if sentiment.get("score", 0) < agent.sentiment_threshold:
        await agent._trigger_sentiment_alert(
            feedback_data.get("stakeholder_id"), sentiment, feedback_record
        )

    return {
        "feedback_id": feedback_id,
        "stakeholder_id": feedback_record["stakeholder_id"],
        "sentiment": sentiment,
        "alert_triggered": sentiment.get("score", 0) < agent.sentiment_threshold,
    }


async def analyze_sentiment(
    agent: StakeholderCommunicationsAgent,
    stakeholder_id: str | None,
) -> dict[str, Any]:
    """Analyze stakeholder sentiment trends."""
    agent.logger.info("Analyzing sentiment for stakeholder: %s", stakeholder_id)

    if stakeholder_id:
        stakeholder_feedback = agent.feedback.get(stakeholder_id, [])
        sentiment_trend = await calculate_sentiment_trend(stakeholder_feedback)
        return {
            "stakeholder_id": stakeholder_id,
            "current_sentiment": sentiment_trend.get("current"),
            "trend": sentiment_trend.get("trend"),
            "feedback_count": len(stakeholder_feedback),
        }
    else:
        overall_sentiment = await calculate_overall_sentiment(agent)
        return {
            "overall_sentiment": overall_sentiment,
            "stakeholders_analyzed": len(agent.feedback),
        }
