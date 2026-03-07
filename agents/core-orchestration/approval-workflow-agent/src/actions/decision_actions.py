"""
Decision recording action for the Approval Workflow Agent.

Handles recording approval/rejection decisions with audit trails,
metrics, and event publishing.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from actions.notification_delivery import record_response_metric

if TYPE_CHECKING:
    from approval_workflow_agent import ApprovalWorkflowAgent


async def record_decision(
    agent: ApprovalWorkflowAgent,
    *,
    approval_id: str,
    decision: str,
    approver_id: str,
    comments: str | None,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    response_time_seconds = None
    existing = agent.approval_store.get(tenant_id, approval_id)
    if existing:
        created_at = existing.get("details", {}).get("chain", {}).get("created_at")
        if created_at:
            try:
                created_dt = datetime.fromisoformat(created_at)
                response_time_seconds = (
                    datetime.now(timezone.utc) - created_dt.replace(tzinfo=timezone.utc)
                ).total_seconds()
            except ValueError:
                response_time_seconds = None
    agent.approval_store.update(
        tenant_id,
        approval_id,
        decision,
        {
            "decision": decision,
            "decided_by": approver_id,
            "decided_at": datetime.now(timezone.utc).isoformat(),
            "comments": comments,
            "response_time_seconds": response_time_seconds,
        },
    )
    agent._emit_audit_event(
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        action="approval.decision",
        outcome="success",
        resource_id=approval_id,
        metadata={
            "decision": decision,
            "approver_id": approver_id,
            "comments": comments,
            "risk_score": existing.get("details", {}).get("risk_score") if existing else None,
            "criticality_level": (
                existing.get("details", {}).get("criticality_level") if existing else None
            ),
        },
    )
    if response_time_seconds is not None:
        record_response_metric(
            agent,
            tenant_id=tenant_id,
            approval_id=approval_id,
            approver_id=approver_id,
            response_time_seconds=response_time_seconds,
            decision=decision,
        )
    agent._publish_approval_event(
        event_type="approval.decision",
        tenant_id=tenant_id,
        approval_chain=existing.get("details", {}).get("chain") if existing else {},
        payload={
            "approval_id": approval_id,
            "decision": decision,
            "approver_id": approver_id,
            "comments": comments,
        },
    )
    request_type = existing.get("details", {}).get("request_type") if existing else None
    request_id = existing.get("details", {}).get("request_id") if existing else None
    request_details = existing.get("details", {}).get("request_details") if existing else {}
    if decision == "approved" and request_type == "resource_optimization":
        optimization_id = None
        if isinstance(request_details, dict):
            optimization_id = request_details.get("optimization_id")
        agent._emit_audit_event(
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            action="resource.optimization.approved",
            outcome="success",
            resource_id=request_id or approval_id,
            metadata={
                "approval_id": approval_id,
                "request_id": request_id,
                "optimization_id": optimization_id,
                "approver_id": approver_id,
            },
        )
    if decision in {"approved", "rejected"}:
        agent._publish_approval_event(
            event_type=f"approval.{decision}",
            tenant_id=tenant_id,
            approval_chain=existing.get("details", {}).get("chain") if existing else {},
            payload={
                "approval_id": approval_id,
                "approver_id": approver_id,
                "comments": comments,
            },
        )

    # --- Post-approval hook: auto-create project entity for intake requests ---
    created_project = None
    if decision == "approved" and request_type == "intake":
        created_project = _handle_intake_approval(
            agent,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            approval_id=approval_id,
            request_id=request_id,
            request_details=request_details or {},
            approver_id=approver_id,
        )

    result: dict[str, Any] = {
        "approval_id": approval_id,
        "decision": decision,
        "status": decision,
        "metadata": {
            "risk_score": existing.get("details", {}).get("risk_score") if existing else None,
            "criticality_level": (
                existing.get("details", {}).get("criticality_level") if existing else None
            ),
        },
    }
    if created_project:
        result["created_project"] = created_project
    return result


def _handle_intake_approval(
    agent: ApprovalWorkflowAgent,
    *,
    tenant_id: str,
    correlation_id: str,
    approval_id: str,
    request_id: str | None,
    request_details: dict[str, Any],
    approver_id: str,
) -> dict[str, Any] | None:
    """Create a project entity when an intake request is approved.

    Generates a project stub from the intake request details and publishes
    a ``project.created`` event so downstream agents and the UI can react.
    """
    import uuid

    project_id = f"proj-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()

    # Extract project metadata from the intake request details
    sponsor = request_details.get("sponsor", {})
    business_case = request_details.get("business_case", {})
    project_name = (
        business_case.get("title")
        or business_case.get("summary", "")[:80]
        or f"Project from intake {request_id or approval_id}"
    )

    project_entity = {
        "project_id": project_id,
        "name": project_name,
        "status": "setup_pending",
        "intake_request_id": request_id or approval_id,
        "sponsor": sponsor,
        "business_case_summary": business_case.get("summary", ""),
        "approved_by": approver_id,
        "approved_at": now,
        "created_at": now,
        "tenant_id": tenant_id,
    }

    # Publish project.created event for downstream consumers
    agent._publish_approval_event(
        event_type="project.created",
        tenant_id=tenant_id,
        approval_chain={},
        payload={
            "project_id": project_id,
            "project_name": project_name,
            "intake_request_id": request_id or approval_id,
            "approval_id": approval_id,
            "approved_by": approver_id,
            "status": "setup_pending",
        },
    )

    # Publish real-time notification event for WebSocket consumers
    agent._publish_approval_event(
        event_type="notification.project_created",
        tenant_id=tenant_id,
        approval_chain={},
        payload={
            "project_id": project_id,
            "project_name": project_name,
            "message": f"Project '{project_name}' created from approved intake request.",
            "severity": "info",
            "channel": "realtime",
        },
    )

    agent._emit_audit_event(
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        action="project.created_from_intake",
        outcome="success",
        resource_id=project_id,
        metadata={
            "approval_id": approval_id,
            "intake_request_id": request_id,
            "project_name": project_name,
            "approver_id": approver_id,
        },
    )

    agent.logger.info(
        "Project created from intake approval: project_id=%s, intake=%s",
        project_id,
        request_id,
    )

    return project_entity
