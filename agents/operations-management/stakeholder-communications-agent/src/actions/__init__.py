"""
Action handlers for the Stakeholder & Communications Management Agent.

Each action is implemented as an async function that receives the agent instance
and delegates to the appropriate utilities.
"""

from .briefing_actions import execute_scheduled_briefing, schedule_briefing
from .classify_stakeholder import classify_stakeholder
from .communication_plan import create_communication_plan
from .dashboard_actions import generate_communication_report, get_stakeholder_dashboard
from .delivery_actions import (
    flush_digest_notifications,
    queue_digest_notifications,
    track_delivery_event,
)
from .engagement_actions import track_engagement
from .event_actions import schedule_event
from .feedback_actions import analyze_sentiment, collect_feedback
from .message_actions import (
    edit_message,
    generate_message,
    schedule_message,
    send_message,
    summarize_report,
)
from .preferences_actions import update_communication_preferences
from .register_stakeholder import register_stakeholder

__all__ = [
    "analyze_sentiment",
    "classify_stakeholder",
    "collect_feedback",
    "create_communication_plan",
    "edit_message",
    "execute_scheduled_briefing",
    "flush_digest_notifications",
    "generate_communication_report",
    "generate_message",
    "get_stakeholder_dashboard",
    "queue_digest_notifications",
    "register_stakeholder",
    "schedule_briefing",
    "schedule_event",
    "schedule_message",
    "send_message",
    "summarize_report",
    "track_delivery_event",
    "track_engagement",
    "update_communication_preferences",
]
