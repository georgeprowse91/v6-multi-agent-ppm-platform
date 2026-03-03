"""Action handlers for approving and reviewing changes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from change_actions.submit_change import notify_stakeholders, publish_event, record_change_audit

if TYPE_CHECKING:
    from change_configuration_agent import ChangeConfigurationAgent


async def approve_change(
    agent: ChangeConfigurationAgent,
    change_id: str,
    approval_data: dict[str, Any],
) -> dict[str, Any]:
    """Approve or reject change."""
    agent.logger.info("Processing approval for change: %s", change_id)

    change = agent.change_requests.get(change_id)
    if not change:
        raise ValueError(f"Change request not found: {change_id}")

    # Record approval/rejection
    decision = approval_data.get("decision", "approve")
    approver = approval_data.get("approver")
    comments = approval_data.get("comments", "")

    change["approval_status"] = "Approved" if decision == "approve" else "Rejected"
    change["approved_by"] = approver
    change["approval_date"] = datetime.now(timezone.utc).isoformat()
    change["approval_comments"] = comments

    if decision == "approve":
        change["status"] = "Approved"
    else:
        change["status"] = "Rejected"

    await agent.db_service.store("change_requests", change_id, change)
    await record_change_audit(
        agent,
        change_id,
        "approval_decision",
        actor_id=approver or "unknown",
        details={"decision": decision, "comments": comments},
    )

    itsm_record = change.get("itsm_record", {})
    itsm_id = itsm_record.get("change_id") if isinstance(itsm_record, dict) else None
    if itsm_id:
        await agent.itsm_service.update_ticket(
            itsm_id,
            {"status": change["status"], "approval_status": change["approval_status"]},
        )
    await publish_event(
        agent,
        "change.approved" if decision == "approve" else "change.rejected",
        {
            "event_id": f"change.{decision}:{change_id}",
            "change_id": change_id,
            "status": change["status"],
            "approved_by": approver,
        },
    )
    await notify_stakeholders(
        agent,
        change,
        event_type="change.approved" if decision == "approve" else "change.rejected",
        tenant_id=change.get("tenant_id", "unknown"),
        correlation_id=change.get("correlation_id", str(uuid.uuid4())),
    )

    return {
        "change_id": change_id,
        "approval_status": change["approval_status"],
        "approved_by": approver,
        "next_steps": (
            "Proceed with implementation" if decision == "approve" else "Review and resubmit"
        ),
    }


async def review_change(
    agent: ChangeConfigurationAgent,
    change_id: str,
    review_data: dict[str, Any],
) -> dict[str, Any]:
    """Record peer review decision for change."""
    change = agent.change_requests.get(change_id)
    if not change:
        raise ValueError(f"Change request not found: {change_id}")
    reviewer = review_data.get("reviewer")
    decision = review_data.get("decision", "reviewed")
    comments = review_data.get("comments", "")
    change["review_status"] = decision
    change["reviewed_by"] = reviewer
    change["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    await agent.db_service.store("change_requests", change_id, change)
    await record_change_audit(
        agent,
        change_id,
        "reviewed",
        actor_id=reviewer or "unknown",
        details={"decision": decision, "comments": comments},
    )
    return {
        "change_id": change_id,
        "review_status": decision,
        "reviewed_by": reviewer,
        "comments": comments,
    }
