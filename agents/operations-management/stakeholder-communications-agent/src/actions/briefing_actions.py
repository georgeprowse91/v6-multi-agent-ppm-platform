"""Action handlers for scheduled executive briefing delivery.

Integrates the Stakeholder Communications agent with the briefing
generator API to support periodic delivery of executive briefings.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from ..stakeholder_communications_agent import StakeholderCommunicationsAgent


_BRIEFING_API_TIMEOUT = 30.0


async def schedule_briefing(
    agent: StakeholderCommunicationsAgent,
    tenant_id: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Schedule a recurring executive briefing delivery.

    Args:
        agent: The StakeholderCommunicationsAgent instance.
        tenant_id: Tenant identifier for scoping.
        config: Schedule configuration containing:
            - portfolio_id: Target portfolio (default: "default")
            - audience: Target audience (board, c_suite, pmo, delivery_team)
            - tone: Briefing tone
            - sections: List of sections to include
            - frequency: Delivery frequency (daily, weekly, fortnightly, monthly)
            - recipients: List of recipient identifiers
            - channels: Delivery channels (email, teams, slack)
            - export_format: Export format (pdf, pptx)
    """
    agent.logger.info(
        "Scheduling briefing delivery: audience=%s, frequency=%s, recipients=%d",
        config.get("audience", "c_suite"),
        config.get("frequency", "weekly"),
        len(config.get("recipients", [])),
    )

    schedule_id = f"sched-{uuid.uuid4().hex[:8]}"
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    schedule = {
        "schedule_id": schedule_id,
        "tenant_id": tenant_id,
        "portfolio_id": config.get("portfolio_id", "default"),
        "audience": config.get("audience", "c_suite"),
        "tone": config.get("tone", "formal"),
        "sections": config.get(
            "sections",
            [
                "highlights",
                "risks",
                "financials",
                "schedule",
                "resources",
                "recommendations",
            ],
        ),
        "frequency": config.get("frequency", "weekly"),
        "recipients": config.get("recipients", []),
        "channels": config.get("channels", ["email"]),
        "export_format": config.get("export_format", "pdf"),
        "enabled": config.get("enabled", True),
        "created_at": created_at,
    }

    # Register the schedule with the briefing API if available
    briefing_api_url = os.getenv("WEB_SERVICE_URL", "http://localhost:8501")
    try:
        async with httpx.AsyncClient(timeout=_BRIEFING_API_TIMEOUT) as client:
            response = await client.post(
                f"{briefing_api_url}/api/briefings/schedule",
                json=schedule,
            )
            if response.status_code == 200:
                api_result = response.json()
                schedule["schedule_id"] = api_result.get("schedule_id", schedule_id)
    except (httpx.HTTPError, OSError, ValueError):
        agent.logger.warning("Briefing API unavailable for schedule registration")

    agent._publish_event(
        "briefing.schedule.created",
        {
            "schedule_id": schedule["schedule_id"],
            "tenant_id": tenant_id,
            "frequency": schedule["frequency"],
            "audience": schedule["audience"],
            "recipient_count": len(schedule["recipients"]),
        },
    )

    return {
        "status": "success",
        "action": "schedule_briefing",
        "schedule": schedule,
        "message": (
            f"Briefing schedule created: {schedule['frequency']} delivery "
            f"to {len(schedule['recipients'])} recipients via {', '.join(schedule['channels'])}"
        ),
    }


async def execute_scheduled_briefing(
    agent: StakeholderCommunicationsAgent,
    tenant_id: str,
    schedule: dict[str, Any],
) -> dict[str, Any]:
    """Execute a scheduled briefing — generate, export, and deliver.

    This is called by the scheduling infrastructure when a briefing
    is due for delivery according to its configured frequency.
    """
    agent.logger.info(
        "Executing scheduled briefing: schedule_id=%s, audience=%s",
        schedule.get("schedule_id", "unknown"),
        schedule.get("audience", "c_suite"),
    )

    briefing_api_url = os.getenv("WEB_SERVICE_URL", "http://localhost:8501")
    briefing_data = None
    export_data = None

    # Step 1: Generate briefing
    try:
        async with httpx.AsyncClient(timeout=_BRIEFING_API_TIMEOUT) as client:
            gen_response = await client.post(
                f"{briefing_api_url}/api/briefings/generate",
                json={
                    "portfolio_id": schedule.get("portfolio_id", "default"),
                    "audience": schedule.get("audience", "c_suite"),
                    "tone": schedule.get("tone", "formal"),
                    "sections": schedule.get("sections", []),
                    "format": "markdown",
                },
            )
            if gen_response.status_code == 200:
                briefing_data = gen_response.json()
    except (httpx.HTTPError, OSError, ValueError):
        agent.logger.warning("Failed to generate scheduled briefing")

    if not briefing_data:
        return {
            "status": "error",
            "action": "execute_scheduled_briefing",
            "error": "Failed to generate briefing",
        }

    # Step 2: Export to configured format
    export_format = schedule.get("export_format", "pdf")
    try:
        async with httpx.AsyncClient(timeout=_BRIEFING_API_TIMEOUT) as client:
            export_response = await client.post(
                f"{briefing_api_url}/api/briefings/export",
                json={
                    "briefing_id": briefing_data.get("briefing_id", ""),
                    "export_format": export_format,
                },
            )
            if export_response.status_code == 200:
                export_data = export_response.json()
    except (httpx.HTTPError, OSError, ValueError):
        agent.logger.warning("Failed to export briefing to %s", export_format)

    # Step 3: Deliver to recipients
    recipients = schedule.get("recipients", [])
    channels = schedule.get("channels", ["email"])

    delivery_results: list[dict[str, Any]] = []
    for recipient in recipients:
        for channel in channels:
            try:
                result = await _deliver_to_recipient(
                    agent,
                    tenant_id,
                    briefing_data,
                    export_data,
                    recipient,
                    channel,
                )
                delivery_results.append(result)
            except Exception:
                agent.logger.exception(
                    "Failed to deliver briefing to %s via %s",
                    recipient,
                    channel,
                )
                delivery_results.append(
                    {
                        "recipient": recipient,
                        "channel": channel,
                        "status": "failed",
                    }
                )

    agent._publish_event(
        "briefing.delivered",
        {
            "schedule_id": schedule.get("schedule_id", ""),
            "briefing_id": briefing_data.get("briefing_id", ""),
            "tenant_id": tenant_id,
            "delivery_count": len(delivery_results),
            "success_count": sum(1 for d in delivery_results if d.get("status") == "delivered"),
        },
    )

    return {
        "status": "success",
        "action": "execute_scheduled_briefing",
        "briefing_id": briefing_data.get("briefing_id", ""),
        "deliveries": delivery_results,
    }


async def _deliver_to_recipient(
    agent: StakeholderCommunicationsAgent,
    tenant_id: str,
    briefing_data: dict[str, Any],
    export_data: dict[str, Any] | None,
    recipient: str,
    channel: str,
) -> dict[str, Any]:
    """Deliver a briefing to a single recipient via a specific channel."""
    delivery_id = f"dlv-{uuid.uuid4().hex[:8]}"
    content = briefing_data.get("content", "")
    title = briefing_data.get("title", "Executive Briefing")
    subject = f"{title} — {time.strftime('%Y-%m-%d')}"

    # Build a message payload compatible with the agent's send_via_channel
    stakeholder = {"email": recipient, "name": recipient, "id": recipient}
    message = {
        "id": delivery_id,
        "subject": subject,
        "content": content,
        "channels": [channel],
    }

    try:
        result = await agent._send_via_channel(
            channel,
            stakeholder,
            message,
            content,
            subject_override=subject,
        )
        return {
            "recipient": recipient,
            "channel": channel,
            "status": "delivered",
            "delivery_id": delivery_id,
            "detail": result,
        }
    except Exception as exc:
        agent.logger.warning(
            "Channel delivery failed for %s via %s: %s",
            recipient,
            channel,
            exc,
        )
        return {
            "recipient": recipient,
            "channel": channel,
            "status": "failed",
            "delivery_id": delivery_id,
            "error": str(exc),
        }
