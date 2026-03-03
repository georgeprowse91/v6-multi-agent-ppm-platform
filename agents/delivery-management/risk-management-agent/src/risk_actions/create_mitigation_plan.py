"""Action handler for mitigation plan creation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from risk_utils import (
    calculate_residual_risk,
    create_mitigation_tasks,
    generate_mitigation_plan_id,
    publish_risk_event,
    recommend_mitigation_strategies,
    resolve_mitigation_owner,
    store_risk_dataset,
)

if TYPE_CHECKING:
    from risk_management_agent import RiskManagementAgent


async def create_mitigation_plan(
    agent: RiskManagementAgent, risk_id: str, mitigation_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Create mitigation plan for risk.

    Returns mitigation plan ID and tasks.
    """
    agent.logger.info("Creating mitigation plan for risk: %s", risk_id)

    risk = agent.risk_register.get(risk_id)
    if not risk:
        raise ValueError(f"Risk not found: {risk_id}")

    # Generate plan ID
    plan_id = await generate_mitigation_plan_id()

    # Recommend mitigation strategies
    recommended_strategies = await recommend_mitigation_strategies(agent, risk)
    mitigation_owner = await resolve_mitigation_owner(agent, risk, mitigation_data)
    tasks = mitigation_data.get("tasks", [])
    if not tasks:
        tasks = [
            {
                "title": strategy,
                "description": f"Mitigation action for risk {risk_id}: {strategy}",
                "priority": (
                    "High" if risk.get("score", 0) >= agent.high_risk_threshold else "Medium"
                ),
                "due_date": mitigation_data.get("due_date"),
                "owner": mitigation_owner,
            }
            for strategy in recommended_strategies[:3]
        ]
    created_tasks = await create_mitigation_tasks(
        agent,
        risk,
        tasks,
        mitigation_owner,
    )

    # Create mitigation plan
    mitigation_plan = {
        "plan_id": plan_id,
        "risk_id": risk_id,
        "strategy": mitigation_data.get(
            "strategy", "mitigate"
        ),  # avoid, mitigate, transfer, accept
        "tasks": tasks,
        "created_tasks": created_tasks,
        "budget": mitigation_data.get("budget"),
        "responsible_person": mitigation_owner,
        "due_date": mitigation_data.get("due_date"),
        "status": "Planned",
        "recommended_strategies": recommended_strategies,
        "effectiveness": mitigation_data.get("effectiveness"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Store plan
    agent.mitigation_plans[plan_id] = mitigation_plan

    # Update risk with mitigation plan
    risk["mitigation_plan_id"] = plan_id

    # Calculate residual risk
    residual_risk = await calculate_residual_risk(risk, mitigation_plan)
    risk["residual_risk"] = residual_risk
    if mitigation_plan.get("effectiveness") is None:
        mitigation_plan["effectiveness"] = round(
            max(0.0, 1 - (residual_risk / max(risk.get("score", 1), 1))), 2
        )

    if agent.db_service:
        await agent.db_service.store("mitigation_plans", plan_id, mitigation_plan)
        await agent.db_service.store("risks", risk_id, risk)
        await agent.db_service.store(
            "mitigation_tasks",
            f"{plan_id}-tasks",
            {"plan_id": plan_id, "risk_id": risk_id, "tasks": created_tasks},
        )
    await store_risk_dataset(agent, "mitigation_plans", [mitigation_plan], domain="mitigation")
    await publish_risk_event(
        agent,
        "risk.mitigation_plan_created",
        {"risk_id": risk_id, "plan_id": plan_id, "strategy": mitigation_plan["strategy"]},
    )
    await publish_risk_event(
        agent,
        "risk.mitigation.created",
        {"risk_id": risk_id, "plan_id": plan_id, "task_count": len(created_tasks)},
    )

    return {
        "plan_id": plan_id,
        "risk_id": risk_id,
        "strategy": mitigation_plan["strategy"],
        "tasks": mitigation_plan["tasks"],
        "created_tasks": created_tasks,
        "task_count": len(mitigation_plan["tasks"]),
        "budget": mitigation_plan["budget"],
        "residual_risk": residual_risk,
        "recommended_strategies": recommended_strategies,
    }
