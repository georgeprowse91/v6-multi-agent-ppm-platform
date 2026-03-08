"""
Portfolio Status Action Handlers

Handlers for:
- get_portfolio_status
- submit_portfolio_for_approval
- record_portfolio_decision
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from portfolio_strategy_agent import PortfolioStrategyAgent


async def get_portfolio_status(
    agent: PortfolioStrategyAgent,
    portfolio_id: str | None,
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """Get current portfolio status and performance metrics."""
    agent.logger.info("Getting portfolio status: %s", portfolio_id)

    if portfolio_id:
        record = agent.portfolio_store.get(tenant_id, portfolio_id)
    else:
        records = agent.portfolio_store.list(tenant_id)
        record = records[-1] if records else None

    if not record:
        return {
            "portfolio_id": portfolio_id,
            "total_projects": 0,
            "total_budget": 0,
            "total_value": 0,
            "investment_mix": {},
            "strategic_coverage": {},
            "resource_utilization": 0,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "portfolio_id": record.get("portfolio_id"),
        "total_projects": len(record.get("ranked_projects", [])),
        "total_budget": 0,
        "total_value": 0,
        "investment_mix": {},
        "strategic_coverage": {},
        "resource_utilization": 0,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


async def submit_portfolio_for_approval(
    agent: PortfolioStrategyAgent,
    portfolio_id: str,
    *,
    decision_payload: dict[str, Any],
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Submit a portfolio for approval via the ApprovalWorkflowAgent."""
    if not agent.approval_agent and agent.approval_agent_enabled:
        from approval_workflow_agent import ApprovalWorkflowAgent

        agent.approval_agent = ApprovalWorkflowAgent(config=agent.approval_agent_config)
    if not agent.approval_agent:
        return {"status": "skipped", "reason": "approval_agent_not_configured"}

    approval = await agent.approval_agent.process(
        {
            "request_type": "portfolio_decision",
            "request_id": portfolio_id,
            "requester": decision_payload.get("requester", "system"),
            "details": decision_payload,
            "tenant_id": tenant_id,
            "correlation_id": correlation_id,
            "context": {"tenant_id": tenant_id, "correlation_id": correlation_id},
        }
    )
    if agent.db_service:
        await agent.db_service.store(
            "portfolio_approvals",
            portfolio_id,
            {"portfolio_id": portfolio_id, "approval": approval},
        )
    return approval


async def record_portfolio_decision(
    agent: PortfolioStrategyAgent,
    portfolio_id: str,
    *,
    decision: dict[str, Any],
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Record a portfolio governance decision in the audit log."""
    record = agent.portfolio_store.get(tenant_id, portfolio_id) or {"portfolio_id": portfolio_id}
    decision_entry = {
        "decision_id": str(uuid.uuid4()),
        "portfolio_id": portfolio_id,
        "decision": decision,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    record.setdefault("decision_log", []).append(decision_entry)
    agent.portfolio_store.upsert(tenant_id, portfolio_id, record)
    if agent.db_service:
        await agent.db_service.store(
            "portfolio_decisions", decision_entry["decision_id"], decision_entry
        )
    await agent.event_bus.publish(
        "portfolio.decision.recorded",
        {
            "portfolio_id": portfolio_id,
            "tenant_id": tenant_id,
            "decision": decision_entry,
            "correlation_id": correlation_id,
        },
    )
    return {"status": "recorded", "decision": decision_entry}
