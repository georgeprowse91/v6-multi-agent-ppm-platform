"""Action handler for calculating program health scores."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from program_management_agent import ProgramManagementAgent


async def handle_get_program_health(
    agent: ProgramManagementAgent,
    program_id: str,
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Calculate composite program health score.

    Returns health metrics and recommendations.
    """
    agent.logger.info("Calculating program health for: %s", program_id)

    program = agent.program_store.get(tenant_id, program_id)
    if not program:
        raise ValueError(f"Program not found: {program_id}")

    constituent_projects = program.get("constituent_projects", [])

    # Gather health metrics from domain agents
    schedule_health = await _get_schedule_health(agent, constituent_projects)
    budget_health = await _get_budget_health(agent, constituent_projects)
    risk_health = await _get_risk_health(agent, constituent_projects)
    quality_health = await _get_quality_health(agent, constituent_projects)
    resource_health = await _get_resource_health(agent, constituent_projects)

    # Calculate weighted composite score
    composite_score = (
        schedule_health * agent.health_score_weights["schedule"]
        + budget_health * agent.health_score_weights["budget"]
        + risk_health * agent.health_score_weights["risk"]
        + quality_health * agent.health_score_weights["quality"]
        + resource_health * agent.health_score_weights["resource"]
    )

    benefit_metrics = await agent._compute_benefit_realization_metrics(
        program_id, constituent_projects
    )
    external_signals = await agent._collect_external_health_signals(
        program_id, constituent_projects
    )
    predicted = await agent._predict_program_health(
        {
            "schedule_variance": 1 - schedule_health,
            "cost_variance": 1 - budget_health,
            "risk_indicator": 1 - risk_health,
            "benefit_realization": benefit_metrics.get("realization_rate", 0),
            "external_health": external_signals.get("health_index", 0.0),
            "dependency_load": external_signals.get("dependency_load", 0.0),
        }
    )
    if predicted.get("score") is not None:
        composite_score = float(predicted["score"])

    # Determine health status
    health_status = await _determine_health_status(composite_score)

    # Identify primary concerns
    concerns = await _identify_health_concerns(
        schedule_health, budget_health, risk_health, quality_health, resource_health
    )

    health_payload = {
        "program_id": program_id,
        "composite_score": composite_score,
        "health_status": health_status,
        "metrics": {
            "schedule": schedule_health,
            "budget": budget_health,
            "risk": risk_health,
            "quality": quality_health,
            "resource": resource_health,
        },
        "benefit_metrics": benefit_metrics,
        "prediction": predicted,
        "external_signals": external_signals,
        "concerns": concerns,
        "recommendations": await _generate_health_recommendations(composite_score, concerns),
        "narrative": await agent._generate_program_narrative(
            program,
            schedule_health=schedule_health,
            budget_health=budget_health,
            risk_health=risk_health,
            quality_health=quality_health,
            resource_health=resource_health,
            benefit_metrics=benefit_metrics,
        ),
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }

    if agent.db_service:
        await agent.db_service.store("program_health", program_id, health_payload)
        await agent.db_service.store(
            "program_analytics",
            program_id,
            {
                "program_id": program_id,
                "health_status": health_status,
                "composite_score": composite_score,
            },
        )

    await agent.event_bus.publish(
        "program.health.updated",
        {
            "program_id": program_id,
            "tenant_id": tenant_id,
            "health": health_payload,
        },
    )

    await agent._publish_program_status_update(
        program_id,
        tenant_id=tenant_id,
        correlation_id=str(uuid.uuid4()),
        status_type="health",
        payload={
            "health_score": composite_score,
            "health_status": health_status,
            "concerns": concerns,
        },
    )

    return health_payload


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_schedule_health(agent: ProgramManagementAgent, project_ids: list[str]) -> float:
    """Get schedule health across projects."""
    action = agent.health_actions.get("schedule")
    if agent.schedule_agent and action and project_ids:
        response = await agent.schedule_agent.process(
            {"action": action, "project_ids": project_ids}
        )
        return float(response.get("schedule_health", 0.85))
    return 0.85


async def _get_budget_health(agent: ProgramManagementAgent, project_ids: list[str]) -> float:
    """Get budget health across projects."""
    action = agent.health_actions.get("budget")
    if agent.financial_agent and action and project_ids:
        response = await agent.financial_agent.process(
            {"action": action, "project_ids": project_ids}
        )
        return float(response.get("budget_health", 0.80))
    return 0.80


async def _get_risk_health(agent: ProgramManagementAgent, project_ids: list[str]) -> float:
    """Get risk health across projects."""
    action = agent.health_actions.get("risk")
    if agent.risk_agent and action and project_ids:
        response = await agent.risk_agent.process({"action": action, "project_ids": project_ids})
        return float(response.get("risk_health", 0.75))
    return 0.75


async def _get_quality_health(agent: ProgramManagementAgent, project_ids: list[str]) -> float:
    """Get quality health across projects."""
    action = agent.health_actions.get("quality")
    if agent.quality_agent and action and project_ids:
        response = await agent.quality_agent.process({"action": action, "project_ids": project_ids})
        return float(response.get("quality_health", 0.90))
    return 0.90


async def _get_resource_health(agent: ProgramManagementAgent, project_ids: list[str]) -> float:
    """Get resource health across projects."""
    action = agent.health_actions.get("resource")
    if agent.resource_agent and action and project_ids:
        response = await agent.resource_agent.process(
            {"action": action, "project_ids": project_ids}
        )
        return float(response.get("resource_health", 0.70))
    return 0.70


async def _determine_health_status(composite_score: float) -> str:
    """Determine health status from composite score."""
    if composite_score >= 0.85:
        return "Healthy"
    elif composite_score >= 0.70:
        return "At Risk"
    else:
        return "Critical"


async def _identify_health_concerns(
    schedule: float, budget: float, risk: float, quality: float, resource: float
) -> list[str]:
    """Identify primary health concerns."""
    concerns: list[str] = []
    if schedule < 0.70:
        concerns.append("Schedule variance exceeds acceptable thresholds")
    if budget < 0.70:
        concerns.append("Budget overruns across multiple projects")
    if risk < 0.70:
        concerns.append("High-priority risks not adequately mitigated")
    if quality < 0.70:
        concerns.append("Quality metrics below standards")
    if resource < 0.70:
        concerns.append("Resource over-allocation and bottlenecks")
    return concerns


async def _generate_health_recommendations(
    composite_score: float, concerns: list[str]
) -> list[str]:
    """Generate health improvement recommendations."""
    recommendations: list[str] = []
    for concern in concerns:
        if "schedule" in concern.lower():
            recommendations.append("Review and optimize critical path across projects")
        if "budget" in concern.lower():
            recommendations.append("Conduct cost review and identify savings opportunities")
        if "risk" in concern.lower():
            recommendations.append("Escalate high-priority risks to steering committee")
        if "quality" in concern.lower():
            recommendations.append("Implement additional quality controls and testing")
        if "resource" in concern.lower():
            recommendations.append("Rebalance resource allocation across program")
    return recommendations
