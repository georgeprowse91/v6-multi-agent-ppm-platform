"""Action handler for gate evaluation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from lifecycle_utils import (
    check_criterion,
    get_criterion_description,
    get_gate_criteria,
    get_lifecycle_state,
)
from orchestration import (
    DurableTask,
    DurableWorkflow,
    OrchestrationContext,
)

if TYPE_CHECKING:
    from project_lifecycle_agent import ProjectLifecycleAgent


async def evaluate_gate(
    agent: ProjectLifecycleAgent, project_id: str, gate_name: str, *, tenant_id: str
) -> dict[str, Any]:
    """
    Evaluate phase gate criteria.

    Returns gate evaluation results and readiness score.
    """
    agent.logger.info("Evaluating gate '%s' for project: %s", gate_name, project_id)

    lifecycle_state = await get_lifecycle_state(agent, tenant_id, project_id)
    if not lifecycle_state:
        raise ValueError(f"Lifecycle state not found for project: {project_id}")

    workflow = DurableWorkflow(
        name="gate_evaluation",
        tasks=[
            DurableTask(
                name="evaluate_criteria",
                action=lambda ctx: _evaluate_gate_criteria(agent, ctx),
            ),
            DurableTask(
                name="score_readiness",
                action=lambda ctx: _score_gate_readiness(agent, ctx),
            ),
            DurableTask(
                name="persist_gate_evaluation",
                action=lambda ctx: _persist_gate_evaluation(agent, ctx),
            ),
            DurableTask(
                name="publish_gate_event",
                action=lambda ctx: _publish_gate_event(agent, ctx),
            ),
            DurableTask(
                name="sync_gate_event",
                action=lambda ctx: _sync_gate_decision(agent, ctx),
            ),
            DurableTask(
                name="summarize_gate",
                action=lambda ctx: _summarize_gate(agent, ctx),
            ),
        ],
        sleep=agent.orchestrator_sleep,
    )
    context = OrchestrationContext(
        workflow_id=f"gate-{project_id}-{gate_name}",
        tenant_id=tenant_id,
        project_id=project_id,
        correlation_id=str(uuid.uuid4()),
        payload={"gate_name": gate_name},
    )
    context = await agent.workflow_engine.run(workflow, context)
    evaluation = context.results["evaluate_criteria"]

    if project_id not in agent.gate_evaluations:
        agent.gate_evaluations[project_id] = []
    agent.gate_evaluations[project_id].append(evaluation)

    return evaluation


# ---------------------------------------------------------------------------
# Workflow task functions
# ---------------------------------------------------------------------------


async def _evaluate_gate_criteria(
    agent: ProjectLifecycleAgent, context: OrchestrationContext
) -> dict[str, Any]:
    gate_name = context.payload.get("gate_name")
    project_id = context.project_id
    gate_criteria_def = await get_gate_criteria(agent, gate_name, tenant_id=context.tenant_id)
    criteria_status = []
    for criterion in gate_criteria_def:
        status = await check_criterion(agent, project_id, criterion)
        criteria_status.append(
            {
                "criterion": criterion,
                "met": status,
                "description": await get_criterion_description(criterion),
            }
        )
    readiness_score = (
        sum(1 for c in criteria_status if c["met"]) / len(criteria_status) if criteria_status else 0
    )
    missing_criteria = [c for c in criteria_status if not c["met"]]
    criteria_met = readiness_score >= 0.90
    evaluation = {
        "project_id": project_id,
        "gate_name": gate_name,
        "criteria_met": criteria_met,
        "gate_status": "passed" if criteria_met else "failed",
        "readiness_score": readiness_score,
        "criteria_status": criteria_status,
        "missing_criteria": missing_criteria,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "recommendation": "Proceed" if criteria_met else "Complete missing activities",
    }
    return evaluation


async def _score_gate_readiness(
    agent: ProjectLifecycleAgent, context: OrchestrationContext
) -> dict[str, Any]:
    evaluation = context.results["evaluate_criteria"]
    health_snapshot = agent.health_scores.get(context.project_id)
    project_data = agent.projects.get(context.project_id, {})
    features = agent.readiness_model.build_features(
        evaluation.get("criteria_status", []), health_snapshot
    )
    ml_score = agent.readiness_model.predict(features)
    readiness_features = agent.readiness_model.build_readiness_features(
        project_data, health_snapshot, evaluation.get("criteria_status", [])
    )
    ai_score = agent.readiness_model.predict_with_ai_service(
        agent.ai_model_service, readiness_features
    )
    evaluation["readiness_score"] = max(evaluation["readiness_score"], ml_score, ai_score or 0.0)
    evaluation["health_snapshot"] = health_snapshot or {}
    evaluation["readiness_model"] = {
        "score": ml_score,
        "trained": agent.readiness_model.trained,
        "ai_score": ai_score,
        "ai_model_id": agent.readiness_model.ai_model_id,
    }
    evaluation["readiness_features"] = readiness_features
    return evaluation


async def _persist_gate_evaluation(
    agent: ProjectLifecycleAgent, context: OrchestrationContext
) -> dict[str, Any]:
    evaluation = context.results["evaluate_criteria"]
    return agent.persistence.store_gate_evaluation(
        context.tenant_id, context.project_id, evaluation
    )


async def _publish_gate_event(
    agent: ProjectLifecycleAgent, context: OrchestrationContext
) -> dict[str, Any]:
    evaluation = context.results["evaluate_criteria"]
    topic = "gate.passed" if evaluation.get("criteria_met") else "gate.failed"
    await agent.event_bus.publish(topic, evaluation)
    return {"topic": topic}


async def _sync_gate_decision(
    agent: ProjectLifecycleAgent, context: OrchestrationContext
) -> dict[str, Any]:
    evaluation = context.results["evaluate_criteria"]
    results = await agent.external_sync.sync_gate_decision(
        context.project_id, evaluation.get("gate_name"), evaluation
    )
    return {"sync_results": [result.__dict__ for result in results]}


async def _summarize_gate(
    agent: ProjectLifecycleAgent, context: OrchestrationContext
) -> dict[str, Any]:
    evaluation = context.results["evaluate_criteria"]
    summary_payload = {"gate_name": evaluation.get("gate_name"), **evaluation}
    summary = await agent.summarizer.summarize(summary_payload)
    record = {
        "project_id": context.project_id,
        "gate_name": evaluation.get("gate_name"),
        "summary": summary["summary"],
        "provider": summary["provider"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await _store_gate_summary(agent, context.tenant_id, record)
    return record


async def _store_gate_summary(
    agent: ProjectLifecycleAgent, tenant_id: str, record: dict[str, Any]
) -> None:
    if agent.knowledge_agent:
        await agent.knowledge_agent.process(
            {
                "action": "ingest_document",
                "document": {
                    "document_id": f"gate-summary-{record['project_id']}-{record['gate_name']}",
                    "title": f"Gate Summary: {record['gate_name']}",
                    "content": record["summary"],
                    "metadata": record,
                },
                "tenant_id": tenant_id,
            }
        )
    else:
        agent.persistence.store_summary(tenant_id, record["project_id"], record)
