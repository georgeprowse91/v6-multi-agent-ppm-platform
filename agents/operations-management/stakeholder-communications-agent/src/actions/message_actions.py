"""Action handlers: generate_message, edit_message, send_message, schedule_message, summarize_report"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from ..stakeholder_utils import (
    build_delivery_schedule,
    calculate_optimal_send_time,
    generate_message_content,
    generate_message_id,
    get_template,
    has_consent,
    load_stakeholder,
    personalize_content,
    publish_event,
    publish_metrics_event,
    record_communication_history,
    resolve_delivery_channels,
    safe_format_template,
    send_via_channel,
    trigger_workflow,
)
from ..stakeholder_utils import (
    summarize_report as _summarize_report_util,
)

if TYPE_CHECKING:
    from ..stakeholder_communications_agent import StakeholderCommunicationsAgent


async def generate_message(
    agent: StakeholderCommunicationsAgent,
    message_data: dict[str, Any],
) -> dict[str, Any]:
    """Generate personalized message."""
    agent.logger.info("Generating message: %s", message_data.get("subject"))

    message_id = await generate_message_id()

    stakeholder_ids = message_data.get("stakeholder_ids", [])

    template_id = message_data.get("template_id")
    locale = message_data.get("locale") or agent.default_locale
    template_payload = get_template(agent, template_id, locale) if template_id else {}
    template_body = message_data.get("template", template_payload.get("body", ""))
    template_subject = message_data.get("subject", template_payload.get("subject"))

    summary = None
    if message_data.get("report") or message_data.get("summary_source"):
        summary = await _summarize_report_util(
            agent,
            message_data.get("report") or message_data.get("summary_source", ""),
            message_data.get("summary_role", "general"),
            locale,
        )

    message_payload = dict(message_data.get("data", {}))
    if summary:
        message_payload["summary"] = summary.get("summary")

    content, generation_metadata = await generate_message_content(
        agent,
        template_body,
        message_payload,
        message_data.get("prompt_type"),
        message_data.get("prompt"),
    )
    subject = template_subject or message_data.get("subject", "")
    if subject:
        subject = safe_format_template(subject, message_payload)

    personalized_messages = []
    for stakeholder_id in stakeholder_ids:
        stakeholder = agent.stakeholder_register.get(stakeholder_id)
        if stakeholder:
            personalized_content = await personalize_content(content, stakeholder)
            if subject:
                personalized_subject = await personalize_content(subject, stakeholder)
            else:
                personalized_subject = ""
            delivery_time = await calculate_optimal_send_time(
                stakeholder,
                message_data.get("scheduled_send"),
            )
            personalized_messages.append(
                {
                    "stakeholder_id": stakeholder_id,
                    "content": personalized_content,
                    "subject": personalized_subject,
                    "scheduled_time": delivery_time,
                }
            )

    message = {
        "message_id": message_id,
        "project_id": message_data.get("project_id"),
        "subject": subject or message_data.get("subject"),
        "content": content,
        "generation_metadata": generation_metadata,
        "personalized_messages": personalized_messages,
        "channel": message_data.get("channel", "email"),
        "scheduled_send": message_data.get("scheduled_send"),
        "delivery_mode": message_data.get("delivery_mode", "immediate"),
        "attachments": message_data.get("attachments", []),
        "status": "Draft",
        "review_required": generation_metadata.get("provider") == "azure_openai",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    agent.messages[message_id] = message

    return {
        "message_id": message_id,
        "subject": message["subject"],
        "recipients": len(personalized_messages),
        "channel": message["channel"],
        "status": "Draft",
        "preview": content[:200],
    }


async def edit_message(
    agent: StakeholderCommunicationsAgent,
    message_id: str | None,
    message_data: dict[str, Any],
) -> dict[str, Any]:
    """Edit a draft message before sending."""
    if not message_id or message_id not in agent.messages:
        raise ValueError("Message not found for editing")
    message = agent.messages[message_id]
    if "subject" in message_data:
        message["subject"] = message_data.get("subject")
    if "content" in message_data:
        message["content"] = message_data.get("content")
    if "template" in message_data or "data" in message_data:
        content, generation_metadata = await generate_message_content(
            agent,
            message_data.get("template", message.get("content", "")),
            message_data.get("data", {}),
            message_data.get("prompt_type"),
            message_data.get("prompt"),
        )
        message["content"] = content
        message["generation_metadata"] = generation_metadata
    personalized_messages = []
    for personalized in message.get("personalized_messages", []):
        stakeholder_id = personalized.get("stakeholder_id")
        stakeholder = agent.stakeholder_register.get(stakeholder_id)
        if stakeholder:
            personalized_content = await personalize_content(message["content"], stakeholder)
            personalized_messages.append(
                {"stakeholder_id": stakeholder_id, "content": personalized_content}
            )
    message["personalized_messages"] = personalized_messages
    message["status"] = "Draft"
    return {
        "message_id": message_id,
        "status": "Draft",
        "subject": message.get("subject"),
        "preview": message.get("content", "")[:200],
    }


async def schedule_message(
    agent: StakeholderCommunicationsAgent,
    tenant_id: str,
    message_id: str,
) -> dict[str, Any]:
    """Schedule message delivery in batches."""
    message = agent.messages.get(message_id)
    if not message:
        raise ValueError(f"Message not found: {message_id}")
    batch_schedule = build_delivery_schedule(
        agent,
        message.get("personalized_messages", []),
        message.get("scheduled_send"),
    )
    message["delivery_batches"] = batch_schedule
    message["status"] = "Scheduled"
    message["scheduled_at"] = datetime.now(timezone.utc).isoformat()
    return {
        "message_id": message_id,
        "status": "Scheduled",
        "batch_count": len(batch_schedule),
        "schedule": batch_schedule,
    }


async def send_message(
    agent: StakeholderCommunicationsAgent,
    tenant_id: str,
    message_id: str,
) -> dict[str, Any]:
    """Send message to stakeholders."""
    agent.logger.info("Sending message: %s", message_id)

    message = agent.messages.get(message_id)
    if not message:
        raise ValueError(f"Message not found: {message_id}")
    if message.get("delivery_mode") == "scheduled":
        scheduled = await schedule_message(agent, tenant_id, message_id)
        return {
            "message_id": message_id,
            "status": "Scheduled",
            "batch_count": scheduled.get("batch_count"),
        }
    if message.get("delivery_mode") == "digest":
        from .delivery_actions import queue_digest_notifications

        queued = await queue_digest_notifications(agent, tenant_id, message)
        return {
            "message_id": message_id,
            "status": "Queued",
            "queued_notifications": queued,
        }

    channel = message.get("channel", "email")
    delivery_results = []

    for personalized in message.get("personalized_messages", []):
        stakeholder_id = personalized.get("stakeholder_id")
        stakeholder = load_stakeholder(agent, tenant_id, stakeholder_id)

        if not stakeholder:
            continue
        delivery_channels = resolve_delivery_channels(message, stakeholder)
        for delivery_channel in delivery_channels:
            if not await has_consent(stakeholder, delivery_channel):
                delivery_results.append(
                    {
                        "stakeholder_id": stakeholder_id,
                        "channel": delivery_channel,
                        "status": "skipped_no_consent",
                        "sent_at": None,
                    }
                )
                continue

            result = await send_via_channel(
                agent,
                delivery_channel,
                stakeholder,
                message,
                personalized.get("content"),
                personalized.get("subject"),
            )

            delivery_results.append(
                {
                    "stakeholder_id": stakeholder_id,
                    "channel": delivery_channel,
                    "status": result.get("status"),
                    "sent_at": result.get("sent_at"),
                }
            )

            if stakeholder_id in agent.engagement_metrics:
                agent.engagement_metrics[stakeholder_id]["messages_sent"] += 1

    message["status"] = "Sent"
    message["sent_at"] = datetime.now(timezone.utc).isoformat()
    message["delivery_results"] = delivery_results

    record_communication_history(
        agent,
        {
            "stakeholder_id": None,
            "channel": channel,
            "subject": message.get("subject"),
            "status": "sent",
            "content": message.get("content"),
            "metadata": {
                "message_id": message_id,
                "delivery_results": delivery_results,
            },
        },
    )
    publish_metrics_event(
        agent,
        tenant_id=tenant_id,
        event_type="message_sent",
        payload={
            "message_id": message_id,
            "channel": channel,
            "delivery_results": delivery_results,
        },
    )
    publish_event(
        agent,
        "stakeholder.message.sent",
        {"message_id": message_id, "delivery_results": delivery_results},
    )
    trigger_workflow(
        agent,
        "stakeholder.message.sent",
        {"message_id": message_id, "delivery_results": delivery_results},
    )

    return {
        "message_id": message_id,
        "status": "Sent",
        "recipients": len(delivery_results),
        "successful_deliveries": len([r for r in delivery_results if r["status"] == "delivered"]),
        "sent_at": message["sent_at"],
    }


async def summarize_report(
    agent: StakeholderCommunicationsAgent,
    report: str,
    role: str,
    locale: str | None,
) -> dict[str, Any]:
    """Summarize a report into concise content for a role."""
    return await _summarize_report_util(agent, report, role, locale)
