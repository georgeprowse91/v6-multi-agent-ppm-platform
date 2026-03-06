"""Action handler: schedule_event"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from ..stakeholder_utils import (
    generate_event_id,
    generate_meeting_agenda,
    propose_optimal_time,
    publish_event,
    record_communication_history,
    trigger_workflow,
)

if TYPE_CHECKING:
    from ..stakeholder_communications_agent import StakeholderCommunicationsAgent


async def schedule_event(
    agent: StakeholderCommunicationsAgent,
    event_data: dict[str, Any],
) -> dict[str, Any]:
    """Schedule event or meeting."""
    agent.logger.info("Scheduling event: %s", event_data.get("title"))

    event_id = await generate_event_id()

    meeting_suggestions = await agent._suggest_meeting_times(
        event_data.get("stakeholder_ids", []),
        event_data.get("duration", 60),
        event_data.get("time_window"),
    )
    optimal_time = (
        meeting_suggestions[0]
        if meeting_suggestions
        else await propose_optimal_time(
            event_data.get("stakeholder_ids", []), event_data.get("duration", 60)
        )
    )

    agenda = event_data.get("agenda", [])
    if not agenda and event_data.get("generate_agenda", True):
        agenda = await generate_meeting_agenda(agent, event_data)

    event = {
        "event_id": event_id,
        "project_id": event_data.get("project_id"),
        "title": event_data.get("title"),
        "description": event_data.get("description"),
        "scheduled_time": event_data.get("scheduled_time", optimal_time),
        "duration_minutes": event_data.get("duration", 60),
        "stakeholder_ids": event_data.get("stakeholder_ids", []),
        "agenda": agenda,
        "location": event_data.get("location", "virtual"),
        "meeting_link": event_data.get("meeting_link"),
        "rsvp_status": {},
        "status": "Scheduled",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    graph_event = None
    if event_data.get("use_graph", True):
        graph_event = await agent._create_graph_event(event, event_data.get("attachments", []))
        if graph_event.get("online_meeting_url"):
            event["meeting_link"] = graph_event.get("online_meeting_url")
        if graph_event.get("scheduled_time"):
            event["scheduled_time"] = graph_event.get("scheduled_time")
        event["graph_event_id"] = graph_event.get("event_id")

    agent.events[event_id] = event

    record_communication_history(
        agent,
        {
            "stakeholder_id": None,
            "channel": "calendar",
            "subject": event.get("title"),
            "status": "scheduled",
            "content": event.get("description"),
            "metadata": {
                "event_id": event_id,
                "meeting_link": event.get("meeting_link"),
                "graph_event": graph_event,
            },
        },
    )
    publish_event(
        agent,
        "stakeholder.meeting.scheduled",
        {
            "event_id": event_id,
            "scheduled_time": event.get("scheduled_time"),
            "meeting_link": event.get("meeting_link"),
        },
    )
    trigger_workflow(
        agent,
        "stakeholder.meeting.scheduled",
        {
            "event_id": event_id,
            "scheduled_time": event.get("scheduled_time"),
            "meeting_link": event.get("meeting_link"),
        },
    )

    return {
        "event_id": event_id,
        "title": event["title"],
        "scheduled_time": event["scheduled_time"],
        "invitees": len(event["stakeholder_ids"]),
        "optimal_time_suggested": optimal_time,
        "meeting_suggestions": meeting_suggestions,
    }
