"""
Approval creation logic for the Approval Workflow Agent.

Handles determining approvers, creating the approval chain,
risk assessment, and delegation application.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from approval_workflow_agent import ApprovalWorkflowAgent


def assess_risk_and_criticality(*, request_type: str, details: dict[str, Any]) -> tuple[str, str]:
    amount = float(details.get("amount") or 0)
    urgency = str(details.get("urgency", "medium")).lower()
    strategic_importance = str(details.get("strategic_importance", "medium")).lower()
    project_type = str(details.get("project_type", "")).lower()

    risk_score = "low"
    if amount >= 100000 or urgency == "high" or request_type in {"phase_gate", "procurement"}:
        risk_score = "high"
    elif amount >= 25000 or urgency == "medium" or request_type == "scope_change":
        risk_score = "medium"

    criticality_level = "normal"
    if strategic_importance in {"critical", "high"} or project_type in {
        "regulatory",
        "security",
    }:
        criticality_level = "critical"
    elif urgency == "high" or strategic_importance == "medium":
        criticality_level = "high"

    return risk_score, criticality_level


def resolve_escalation_timeout(
    agent: ApprovalWorkflowAgent, *, risk_score: str, criticality_level: str
) -> float:
    base_timeout = float(agent.approval_policies.get("escalation_timeout_hours", 48))
    risk_thresholds = agent.approval_policies.get("risk_thresholds", {})
    criticality_levels = agent.approval_policies.get("criticality_levels", {})

    risk_timeout = float(risk_thresholds.get(risk_score, base_timeout))
    criticality_timeout = float(criticality_levels.get(criticality_level, base_timeout))
    return min(risk_timeout, criticality_timeout)


async def determine_approvers(
    agent: ApprovalWorkflowAgent,
    tenant_id: str,
    request_type: str,
    details: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]], dict[str, list[str]]]:
    """Determine required approvers based on request type and thresholds."""
    roles: list[str] = []

    if request_type == "budget_change":
        amount = details.get("amount", 0)

        # Threshold-based routing
        if amount < 10000:
            roles = ["project_manager"]
        elif amount < 50000:
            roles = ["project_manager", "sponsor"]
        elif amount < 100000:
            roles = ["project_manager", "sponsor", "finance_director"]
        else:
            roles = ["project_manager", "sponsor", "finance_director", "cfo"]

    elif request_type == "scope_change":
        roles = ["project_manager", "sponsor", "change_control_board"]

    elif request_type == "procurement":
        amount = details.get("amount", 0)
        if amount < 25000:
            roles = ["project_manager"]
        else:
            roles = ["project_manager", "procurement_manager", "finance_director"]

    elif request_type == "phase_gate":
        roles = ["project_manager", "sponsor", "steering_committee"]

    elif request_type == "resource_change":
        roles = ["project_manager", "resource_manager"]
    elif request_type == "resource_optimization":
        roles = ["project_manager", "resource_manager", "portfolio_manager"]

    resolved = await agent.role_lookup.get_users_for_roles(tenant_id, roles)
    approvers = []
    user_roles: dict[str, list[str]] = {}
    for role in roles:
        role_users = resolved.get(role, [])
        approvers.extend(role_users)
        for user_id in role_users:
            user_roles.setdefault(user_id, []).append(role)
    approvers = list(dict.fromkeys(approvers))

    approvers, delegation_records = apply_delegations(agent, approvers)
    return approvers, delegation_records, user_roles


async def create_approval_chain(
    agent: ApprovalWorkflowAgent,
    *,
    tenant_id: str,
    request_id: str,
    request_type: str,
    approvers: list[str],
    details: dict[str, Any],
    delegation_records: list[dict[str, Any]],
    user_roles: dict[str, list[str]],
    risk_score: str,
    criticality_level: str,
    escalation_timeout_hours: float,
) -> dict[str, Any]:
    """Create approval chain configuration."""
    approval_id = f"approval_{request_id}_{datetime.now(timezone.utc).timestamp()}"

    # Determine chain type based on request
    chain_type = "sequential" if len(approvers) > 2 else "parallel"

    # Calculate deadline based on urgency
    urgency = details.get("urgency", "medium")
    deadline_hours = {"high": 24, "medium": 72, "low": 120}
    deadline = datetime.now(timezone.utc) + timedelta(hours=deadline_hours[urgency])

    chain = {
        "id": approval_id,
        "request_id": request_id,
        "request_type": request_type,
        "type": chain_type,
        "approvers": approvers,
        "deadline": deadline.isoformat(),
        "current_step": 0,
        "responses": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "delegations": delegation_records,
        "user_roles": user_roles,
        "risk_score": risk_score,
        "criticality_level": criticality_level,
        "escalation_timeout_hours": escalation_timeout_hours,
    }

    agent.approval_chains[approval_id] = chain
    agent.approval_store.create(
        tenant_id,
        approval_id,
        {
            "request_type": request_type,
            "request_id": request_id,
            "request_details": details,
            "approvers": approvers,
            "user_roles": user_roles,
            "risk_score": risk_score,
            "criticality_level": criticality_level,
            "escalation_timeout_hours": escalation_timeout_hours,
            "chain": chain,
            "notifications": [],
        },
    )

    return chain


def apply_delegations(
    agent: ApprovalWorkflowAgent, approvers: list[str]
) -> tuple[list[str], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    resolved: list[str] = []
    now = datetime.now(timezone.utc)
    for approver in approvers:
        if not agent.delegation_enabled:
            resolved.append(approver)
            continue
        delegate = agent.delegation_client.get_delegate(approver, now)
        if delegate:
            active_rule = agent.delegation_client.get_active_rule(approver, now) or {}
            records.append(
                {
                    "delegator": approver,
                    "delegate": delegate,
                    "start": active_rule.get("start", now).isoformat(),
                    "end": active_rule.get("end", now).isoformat(),
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            resolved.append(delegate)
        else:
            resolved.append(approver)
    return list(dict.fromkeys(resolved)), records
