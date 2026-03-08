"""Action handler for health monitoring and reporting."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from lifecycle_utils import (
    detect_warnings,
    determine_health_status,
    get_metric_status,
    publish_health_report_generated,
    publish_health_updated,
)
from orchestration import (
    DurableTask,
    DurableWorkflow,
    OrchestrationContext,
)

from agents.common.health_recommendations import generate_recommendations, identify_health_concerns
from agents.common.metrics_catalog import get_metric_value, normalize_metric_value

if TYPE_CHECKING:
    from project_lifecycle_agent import ProjectLifecycleAgent


async def monitor_health(
    agent: ProjectLifecycleAgent, project_id: str, *, tenant_id: str
) -> dict[str, Any]:
    """
    Monitor project health continuously.

    Returns composite health score and metrics from domain agents.
    """
    agent.logger.info("Monitoring health for project: %s", project_id)

    project = agent.projects.get(project_id)
    if not project:
        raise ValueError(f"Project not found: {project_id}")

    metric_context = {
        "tenant_id": tenant_id,
        "schedule_id": project.get("schedule_id"),
        "resource_filters": project.get("resource_filters", {}),
    }
    raw_schedule, raw_cost, raw_risk, raw_quality, raw_resource = await asyncio.gather(
        get_metric_value(
            "schedule_variance",
            project_id,
            tenant_id=tenant_id,
            context=metric_context,
            agent_clients=agent.metric_agents,
            fallback=project,
        ),
        get_metric_value(
            "cost_variance",
            project_id,
            tenant_id=tenant_id,
            context=metric_context,
            agent_clients=agent.metric_agents,
            fallback=project,
        ),
        get_metric_value(
            "risk_score",
            project_id,
            tenant_id=tenant_id,
            context=metric_context,
            agent_clients=agent.metric_agents,
            fallback=project,
        ),
        get_metric_value(
            "quality_score",
            project_id,
            tenant_id=tenant_id,
            context=metric_context,
            agent_clients=agent.metric_agents,
            fallback=project,
        ),
        get_metric_value(
            "resource_utilization",
            project_id,
            tenant_id=tenant_id,
            context=metric_context,
            agent_clients=agent.metric_agents,
            fallback=project,
        ),
    )

    raw_metrics = {
        "schedule_variance": raw_schedule,
        "cost_variance": raw_cost,
        "risk_score": raw_risk,
        "quality_score": raw_quality,
        "resource_utilization": raw_resource,
    }

    schedule_health = normalize_metric_value("schedule_variance", raw_schedule)
    cost_health = normalize_metric_value("cost_variance", raw_cost)
    risk_health = normalize_metric_value("risk_score", raw_risk)
    quality_health = normalize_metric_value("quality_score", raw_quality)
    resource_health = normalize_metric_value("resource_utilization", raw_resource)

    # Calculate composite health score
    composite_score = (
        schedule_health * agent.health_score_weights["schedule"]
        + cost_health * agent.health_score_weights["cost"]
        + risk_health * agent.health_score_weights["risk"]
        + quality_health * agent.health_score_weights["quality"]
        + resource_health * agent.health_score_weights["resource"]
    )

    # Determine health status
    health_status = await determine_health_status(composite_score)

    # Identify concerns and anomalies
    concerns = identify_health_concerns(
        {
            "schedule": schedule_health,
            "cost": cost_health,
            "risk": risk_health,
            "quality": quality_health,
            "resource": resource_health,
        }
    )

    # Detect early warning signals
    warnings = await detect_warnings(agent, project_id, raw_metrics)

    # Generate recommendations
    recommendations = generate_recommendations(concerns)

    health_data = {
        "project_id": project_id,
        "composite_score": composite_score,
        "health_status": health_status,
        "metrics": {
            "schedule": {
                "score": schedule_health,
                "status": await get_metric_status(schedule_health),
                "raw": raw_schedule,
            },
            "cost": {
                "score": cost_health,
                "status": await get_metric_status(cost_health),
                "raw": raw_cost,
            },
            "risk": {
                "score": risk_health,
                "status": await get_metric_status(risk_health),
                "raw": raw_risk,
            },
            "quality": {
                "score": quality_health,
                "status": await get_metric_status(quality_health),
                "raw": raw_quality,
            },
            "resource": {
                "score": resource_health,
                "status": await get_metric_status(resource_health),
                "raw": raw_resource,
            },
        },
        "raw_metrics": raw_metrics,
        "concerns": concerns,
        "warnings": warnings,
        "recommendations": recommendations,
        "monitored_at": datetime.now(timezone.utc).isoformat(),
    }

    workflow = DurableWorkflow(
        name="health_monitoring",
        tasks=[
            DurableTask(
                name="persist_health",
                action=lambda ctx: _persist_health_metrics(agent, ctx),
            ),
            DurableTask(
                name="publish_health",
                action=lambda ctx: _publish_health_event(agent, ctx),
            ),
            DurableTask(
                name="notify_health",
                action=lambda ctx: _notify_health_if_needed(agent, ctx),
            ),
        ],
        sleep=agent.orchestrator_sleep,
    )
    context = OrchestrationContext(
        workflow_id=f"health-{project_id}",
        tenant_id=tenant_id,
        project_id=project_id,
        correlation_id=str(uuid.uuid4()),
        payload={"health_data": health_data},
    )
    await agent.workflow_engine.run(workflow, context)

    return health_data


async def generate_health_report(
    agent: ProjectLifecycleAgent, project_id: str, *, tenant_id: str
) -> dict[str, Any]:
    """
    Generate a standardized health report and publish it as an event.
    """
    health_data = await monitor_health(agent, project_id, tenant_id=tenant_id)
    report_id = f"health-report-{project_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    summary = (
        f"Project health is {health_data.get('health_status')} with "
        f"composite score {health_data.get('composite_score', 0):.2f}."
    )
    report = {
        "report_id": report_id,
        "project_id": project_id,
        "summary": summary,
        "health_status": health_data.get("health_status"),
        "composite_score": health_data.get("composite_score"),
        "metrics": health_data.get("metrics", {}),
        "concerns": health_data.get("concerns", []),
        "warnings": health_data.get("warnings", []),
        "recommendations": health_data.get("recommendations", []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    await publish_health_report_generated(agent, report, tenant_id=tenant_id)
    return report


# ---------------------------------------------------------------------------
# Workflow task functions
# ---------------------------------------------------------------------------


async def _persist_health_metrics(
    agent: ProjectLifecycleAgent, context: OrchestrationContext
) -> dict[str, Any]:
    health_data = context.payload["health_data"]
    project_id = context.project_id
    agent.health_scores[project_id] = health_data
    record_id = f"{project_id}-{health_data['monitored_at']}"
    agent.health_store.upsert(context.tenant_id, record_id, health_data.copy())
    agent.monitor_client.record_metric(
        "lifecycle.health.composite",
        float(health_data.get("composite_score", 0.0)),
        metadata={"project_id": project_id, "tenant_id": context.tenant_id},
    )
    return agent.persistence.store_health_metrics(context.tenant_id, project_id, health_data)


async def _publish_health_event(
    agent: ProjectLifecycleAgent, context: OrchestrationContext
) -> dict[str, Any]:
    health_data = context.payload["health_data"]
    await publish_health_updated(
        agent,
        context.project_id,
        health_data,
        tenant_id=context.tenant_id,
    )
    return {"status": "published"}


async def _notify_health_if_needed(
    agent: ProjectLifecycleAgent, context: OrchestrationContext
) -> dict[str, Any]:
    health_data = context.payload["health_data"]
    if health_data.get("health_status") == "Critical":
        return await agent.notification_service.notify_gate_decision(
            {
                "project_id": context.project_id,
                "event": "project.health.critical",
                "health_data": health_data,
            }
        )
    return {"status": "skipped", "reason": "health_not_critical"}
