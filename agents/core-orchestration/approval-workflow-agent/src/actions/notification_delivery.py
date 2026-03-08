"""
Notification delivery logic for the Approval Workflow Agent.

Handles sending, dispatching, digest queuing, preference resolution,
and delivery metrics for approval notifications.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from approval_workflow_agent import ApprovalWorkflowAgent


async def send_approval_notifications(
    agent: ApprovalWorkflowAgent,
    *,
    tenant_id: str,
    approval_chain: dict[str, Any],
    approvers: list[str],
    details: dict[str, Any],
) -> bool:
    """Send approval notifications to approvers across configured channels."""
    webhook = os.getenv("NOTIFICATION_WEBHOOK_URL")
    notification_results: list[bool] = []
    payloads: list[dict[str, Any]] = []

    for approver in approvers:
        agent.logger.info("Sending approval notification to %s", approver)
        delegation_details = find_delegation_details(approval_chain, approver)
        notification_recipient = resolve_notification_recipient(
            agent,
            tenant_id=tenant_id,
            approver=approver,
            delegation_details=delegation_details,
        )
        context = build_notification_context(
            tenant_id=tenant_id,
            approval_chain=approval_chain,
            approver=approver,
            details=details,
            delegation_details=delegation_details,
        )
        preferences = resolve_notification_preferences(
            agent,
            tenant_id=tenant_id,
            approver=notification_recipient,
            approval_chain=approval_chain,
        )
        locale = preferences.get("locale", agent.template_engine.default_locale)
        accessible_format = preferences.get("accessible_format", "text_only")
        subject = agent.template_engine.render("approval_request_subject", locale, context)
        body, html_body = agent.template_engine.render_accessible(
            template_key="approval_request_body",
            locale=locale,
            context=context,
            accessible_format=accessible_format,
        )
        chat_message = agent.template_engine.render("approval_request_chat", locale, context)
        push_message = agent.template_engine.render("approval_request_push", locale, context)

        notification = {
            "to": notification_recipient,
            "assigned_approver": approver,
            "subject": subject,
            "body": body,
            "deadline": approval_chain["deadline"],
            "approval_id": approval_chain["id"],
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "channels": preferences.get("channels", {}),
            "delivery": preferences.get("delivery", "immediate"),
            "locale": locale,
            "accessible_format": accessible_format,
        }
        result = await dispatch_notification(
            agent,
            tenant_id=tenant_id,
            recipient=notification_recipient,
            notification=notification,
            subject=subject,
            body=body,
            chat_message=chat_message,
            push_message=push_message,
            html_body=html_body,
            preferences=preferences,
        )
        notification_results.append(result)
        agent.notifications.append(notification)
        persist_notification(agent, tenant_id, approval_chain["id"], notification)
        if webhook:
            payloads.append(
                {
                    "user": notification_recipient,
                    "approval_request_id": approval_chain["request_id"],
                    "message": body,
                    "deadline": approval_chain["deadline"],
                }
            )

    if webhook and payloads:
        tasks = [post_webhook(agent, webhook, payload) for payload in payloads]
        await asyncio.gather(*tasks)
    elif not webhook:
        agent.logger.warning(
            "NOTIFICATION_WEBHOOK_URL not set; webhook notifications will be skipped."
        )

    return any(notification_results) or bool(webhook)


async def send_notification(
    agent: ApprovalWorkflowAgent,
    *,
    recipient: str,
    subject: str,
    body: str,
    metadata: dict[str, Any] | None = None,
) -> bool:
    if not agent.notification_service:
        agent.logger.warning(
            "Notification service not initialized; falling back to log-only notification."
        )
        agent.logger.info("Notification to %s: %s", recipient, subject)
        return False
    result = await agent.notification_service.send_email(recipient, subject, body, metadata)
    status = result.get("status")
    if status in {"sent", "sent_mock", "pending"}:
        return True
    agent.logger.warning(
        "Notification service failed to send email to %s with status %s", recipient, status
    )
    return False


async def dispatch_notification(
    agent: ApprovalWorkflowAgent,
    *,
    tenant_id: str,
    recipient: str,
    notification: dict[str, Any],
    subject: str,
    body: str,
    chat_message: str,
    push_message: str,
    html_body: str | None,
    preferences: dict[str, Any],
) -> bool:
    delivery = preferences.get("delivery", "immediate")
    if delivery == "digest":
        queue_digest_notification(
            agent,
            tenant_id=tenant_id,
            recipient=recipient,
            notification=notification,
            subject=subject,
            body=body,
            chat_message=chat_message,
            push_message=push_message,
            html_body=html_body,
            preferences=preferences,
        )
        return True
    return await deliver_notification(
        agent,
        tenant_id=tenant_id,
        recipient=recipient,
        notification=notification,
        subject=subject,
        body=body,
        chat_message=chat_message,
        push_message=push_message,
        html_body=html_body,
        preferences=preferences,
    )


async def deliver_notification(
    agent: ApprovalWorkflowAgent,
    *,
    tenant_id: str,
    recipient: str,
    notification: dict[str, Any],
    subject: str,
    body: str,
    chat_message: str,
    push_message: str,
    html_body: str | None,
    preferences: dict[str, Any],
) -> bool:
    channels = preferences.get("channels", {})
    results: list[bool] = []

    email_channel = channels.get("email")
    if email_channel:
        email_address = (
            email_channel.get("address") if isinstance(email_channel, dict) else email_channel
        )
        results.append(
            await send_notification(
                agent,
                recipient=email_address,
                subject=subject,
                body=body,
                metadata={
                    "approval_id": notification["approval_id"],
                    "deadline": notification["deadline"],
                    "html_body": html_body or channels.get("email_html"),
                    "locale": preferences.get("locale", agent.template_engine.default_locale),
                    "accessible_format": preferences.get("accessible_format", "text_only"),
                },
            )
        )

    teams_channel = channels.get("teams")
    if teams_channel and agent.notification_service:
        teams_result = await agent.notification_service.send_teams_message(
            team_id=teams_channel.get("team_id"),
            channel_id=teams_channel.get("channel_id"),
            message=chat_message,
            chat_id=teams_channel.get("chat_id"),
            user_id=teams_channel.get("user_id"),
        )
        results.append(teams_result.get("status") in {"sent", "sent_mock"})

    slack_channel = channels.get("slack")
    if slack_channel and agent.notification_service:
        slack_result = await agent.notification_service.send_slack_message(
            destination=slack_channel.get("channel") or slack_channel.get("user_id"),
            message=chat_message,
        )
        results.append(slack_result.get("status") in {"sent", "sent_mock"})

    push_channel = channels.get("push")
    if push_channel and agent.notification_service:
        destinations = push_channel.get("destinations", [])
        for destination in destinations:
            push_result = await agent.notification_service.send_push_notification(
                destination, push_message
            )
            results.append(push_result.get("status") in {"sent", "sent_mock"})

    delivered = any(results)
    record_delivery_metric(
        agent,
        tenant_id=tenant_id,
        recipient=recipient,
        approval_id=notification["approval_id"],
        delivered=delivered,
        channels=list(channels.keys()),
    )
    return delivered


def queue_digest_notification(
    agent: ApprovalWorkflowAgent,
    *,
    tenant_id: str,
    recipient: str,
    notification: dict[str, Any],
    subject: str,
    body: str,
    chat_message: str,
    push_message: str,
    html_body: str | None,
    preferences: dict[str, Any],
) -> None:
    key = f"{tenant_id}:{recipient}"
    entry = {
        "notification": notification,
        "subject": subject,
        "body": body,
        "chat_message": chat_message,
        "push_message": push_message,
        "html_body": html_body,
        "preferences": preferences,
    }
    agent.notification_queue.setdefault(key, []).append(entry)
    if key not in agent.digest_tasks or agent.digest_tasks[key].done():
        interval_minutes = preferences.get(
            "digest_interval_minutes"
        ) or agent.approval_policies.get("digest_interval_minutes", 60)
        agent.digest_tasks[key] = asyncio.create_task(
            send_digest_notifications_after_delay(
                agent,
                tenant_id=tenant_id,
                recipient=recipient,
                interval_minutes=interval_minutes,
            )
        )


async def send_digest_notifications_after_delay(
    agent: ApprovalWorkflowAgent,
    *,
    tenant_id: str,
    recipient: str,
    interval_minutes: int,
) -> None:
    await asyncio.sleep(interval_minutes * 60)
    await send_digest_notifications(agent, tenant_id=tenant_id, recipient=recipient)


async def send_digest_notifications(
    agent: ApprovalWorkflowAgent,
    *,
    tenant_id: str,
    recipient: str,
) -> bool:
    key = f"{tenant_id}:{recipient}"
    entries = agent.notification_queue.pop(key, [])
    if not entries:
        return False
    latest = entries[-1]
    preferences = latest["preferences"]
    locale = preferences.get("locale", agent.template_engine.default_locale)
    context = {
        "recipient": recipient,
        "count": len(entries),
        "items": format_digest_entries(entries),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    subject = agent.template_engine.render("approval_digest_subject", locale, context)
    accessible_format = preferences.get("accessible_format", "text_only")
    body, html_body = agent.template_engine.render_accessible(
        template_key="approval_digest_body",
        locale=locale,
        context=context,
        accessible_format=accessible_format,
    )
    return await deliver_notification(
        agent,
        tenant_id=tenant_id,
        recipient=recipient,
        notification=latest["notification"],
        subject=subject,
        body=body,
        chat_message=body,
        push_message=subject,
        html_body=html_body,
        preferences=preferences,
    )


def format_digest_entries(entries: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for entry in entries:
        notification = entry["notification"]
        lines.append(
            f"- {notification['subject']} (approval {notification['approval_id']}, "
            f"deadline {notification['deadline']})"
        )
    return "\n".join(lines)


def build_notification_context(
    *,
    tenant_id: str,
    approval_chain: dict[str, Any],
    approver: str,
    details: dict[str, Any],
    delegation_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    delegation_note = ""
    delegated_from = ""
    if delegation_details:
        delegated_from = str(delegation_details.get("delegator", ""))
        if delegated_from:
            delegation_note = (
                f"You are receiving this approval request on behalf of {delegated_from}."
            )
    return {
        "tenant_id": tenant_id,
        "approval_id": approval_chain["id"],
        "request_id": approval_chain["request_id"],
        "request_type": approval_chain.get("request_type")
        or details.get("request_type")
        or details.get("type")
        or "",
        "description": details.get("description", "Approval required"),
        "justification": details.get("justification", ""),
        "amount": details.get("amount", ""),
        "urgency": details.get("urgency", ""),
        "project_id": details.get("project_id") or approval_chain.get("project_id", ""),
        "deadline": approval_chain["deadline"],
        "approver": approver,
        "delegated_from": delegated_from,
        "delegation_note": delegation_note,
    }


def resolve_notification_preferences(
    agent: ApprovalWorkflowAgent,
    *,
    tenant_id: str,
    approver: str,
    approval_chain: dict[str, Any],
) -> dict[str, Any]:
    routing = (agent.config or {}).get("notification_routing", {})
    default_prefs = routing.get("default", {})
    user_prefs = routing.get("users", {}).get(approver, {})
    group_prefs: dict[str, Any] = {}
    for role in approval_chain.get("user_roles", {}).get(approver, []):
        group_prefs = merge_preferences(group_prefs, routing.get("groups", {}).get(role, {}))
    stored = agent.notification_store.get_preferences(tenant_id, approver) or {}
    preferences = merge_preferences(
        merge_preferences(merge_preferences(default_prefs, group_prefs), user_prefs),
        stored,
    )

    channels = preferences.setdefault("channels", {})
    if not channels.get("email") and "@" in approver:
        channels["email"] = {"address": approver}
    preferences.setdefault("delivery", "immediate")
    preferences.setdefault("locale", agent.template_engine.default_locale)
    accessible = preferences.setdefault("accessible_format", "text_only")
    if accessible not in {"text_only", "html_with_alt_text"}:
        preferences["accessible_format"] = "text_only"
    preferences.setdefault("notify_delegate_directly", True)
    return preferences


def find_delegation_details(approval_chain: dict[str, Any], approver: str) -> dict[str, Any] | None:
    for record in approval_chain.get("delegations", []):
        if record.get("delegate") == approver:
            return record
    return None


def resolve_notification_recipient(
    agent: ApprovalWorkflowAgent,
    *,
    tenant_id: str,
    approver: str,
    delegation_details: dict[str, Any] | None,
) -> str:
    if not delegation_details:
        return approver
    preferences = agent.notification_store.get_preferences(tenant_id, approver) or {}
    if preferences.get("notify_delegate_directly", True):
        return approver
    return str(delegation_details.get("delegator") or approver)


def merge_preferences(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    if not base:
        return dict(override)
    merged = dict(base)
    for key, value in override.items():
        if key == "channels":
            merged.setdefault("channels", {})
            merged["channels"] = {**merged["channels"], **value}
        else:
            merged[key] = value
    return merged


def record_delivery_metric(
    agent: ApprovalWorkflowAgent,
    *,
    tenant_id: str,
    recipient: str,
    approval_id: str,
    delivered: bool,
    channels: list[str],
) -> None:
    metadata = {
        "tenant_id": tenant_id,
        "recipient": recipient,
        "approval_id": approval_id,
        "channels": channels,
    }
    if delivered:
        agent.analytics_client.record_event("approval.notification.sent", metadata)
        agent.analytics_client.record_metric("approval.notification.sent.count", 1, metadata)
    else:
        agent.analytics_client.record_event("approval.notification.failed", metadata)
        agent.analytics_client.record_metric("approval.notification.failed.count", 1, metadata)


def record_interaction_metric(
    agent: ApprovalWorkflowAgent,
    *,
    tenant_id: str,
    recipient: str,
    approval_id: str,
    interaction: str,
) -> None:
    metadata = {
        "tenant_id": tenant_id,
        "recipient": recipient,
        "approval_id": approval_id,
        "interaction": interaction,
    }
    agent.analytics_client.record_event("approval.notification.interaction", metadata)
    agent.analytics_client.record_metric(f"approval.notification.{interaction}.count", 1, metadata)


def record_response_metric(
    agent: ApprovalWorkflowAgent,
    *,
    tenant_id: str,
    approval_id: str,
    approver_id: str,
    response_time_seconds: float,
    decision: str,
) -> None:
    metadata = {
        "tenant_id": tenant_id,
        "approval_id": approval_id,
        "approver_id": approver_id,
        "decision": decision,
    }
    agent.analytics_client.record_metric(
        "approval.response_time.seconds", response_time_seconds, metadata
    )
    agent.analytics_client.record_event("approval.decision.recorded", metadata)
    adjust_delivery_strategy(
        agent,
        tenant_id=tenant_id,
        approver_id=approver_id,
        response_time_seconds=response_time_seconds,
    )


def adjust_delivery_strategy(
    agent: ApprovalWorkflowAgent,
    *,
    tenant_id: str,
    approver_id: str,
    response_time_seconds: float,
) -> None:
    threshold_hours = agent.approval_policies.get("response_time_threshold_hours", 48)
    existing = agent.notification_store.get_preferences(tenant_id, approver_id) or {}
    delivery = existing.get("delivery", "immediate")
    if response_time_seconds > threshold_hours * 3600 and delivery != "digest":
        updated = {**existing, "delivery": "digest"}
        agent.notification_store.upsert_preferences(tenant_id, approver_id, updated)


async def post_webhook(agent: ApprovalWorkflowAgent, url: str, payload: dict[str, Any]) -> None:
    """Post a JSON payload to the configured webhook."""
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json=payload)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            agent.logger.error("Failed to send notification to %s: %s", url, exc)


def persist_notification(
    agent: ApprovalWorkflowAgent,
    tenant_id: str,
    approval_id: str,
    notification: dict[str, Any],
) -> None:
    existing = agent.approval_store.get(tenant_id, approval_id)
    notifications = []
    if existing and isinstance(existing.get("details", {}).get("notifications"), list):
        notifications = list(existing["details"]["notifications"])
    notifications.append(notification)
    details = existing["details"] if existing else {}
    details["notifications"] = notifications
    agent.approval_store.update(tenant_id, approval_id, "pending", details)
