"""Action handler for methodology recommendation and adjustment."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from lifecycle_utils import (
    get_alternative_methodologies,
    load_methodology_map,
    map_phase_to_methodology,
)
from orchestration import (
    DurableTask,
    DurableWorkflow,
    OrchestrationContext,
)

if TYPE_CHECKING:
    from project_lifecycle_agent import ProjectLifecycleAgent


async def recommend_methodology(
    agent: ProjectLifecycleAgent, project_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Recommend appropriate methodology based on project characteristics.

    Returns recommended methodology with rationale.
    """
    agent.logger.info("Recommending methodology")

    # Extract project characteristics
    project_data.get("size", "medium")
    complexity = project_data.get("complexity", "medium")
    requirement_volatility = project_data.get("requirement_volatility", "medium")
    stakeholder_engagement = project_data.get("stakeholder_engagement", "medium")
    regulatory_requirements = project_data.get("regulatory_requirements", False)

    # Simplified rule-based logic
    if requirement_volatility == "high" and stakeholder_engagement == "high":
        methodology = "adaptive"
        rationale = "High requirement volatility and stakeholder engagement favor Adaptive approach"
    elif regulatory_requirements or complexity == "high":
        methodology = "predictive"
        rationale = "Regulatory requirements and high complexity favor Predictive approach"
    else:
        methodology = "hybrid"
        rationale = "Mixed characteristics suggest Hybrid approach for optimal flexibility"

    return {
        "methodology": methodology,
        "rationale": rationale,
        "confidence": 0.85,
        "alternatives": await get_alternative_methodologies(methodology),
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }


async def adjust_methodology(
    agent: ProjectLifecycleAgent,
    project_id: str,
    new_methodology: str,
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Adjust project methodology.

    Returns updated methodology configuration.
    """
    agent.logger.info("Adjusting methodology for project: %s", project_id)

    lifecycle_state = agent.lifecycle_states.get(project_id)
    if not lifecycle_state:
        raise ValueError(f"Lifecycle state not found for project: {project_id}")

    old_methodology = agent.projects[project_id].get("methodology")

    # Load new methodology map
    new_methodology_map = await load_methodology_map(agent, new_methodology, tenant_id=tenant_id)

    # Map current phase to equivalent in new methodology
    current_phase = lifecycle_state.get("current_phase")
    new_phase = await map_phase_to_methodology(
        agent, current_phase, old_methodology, new_methodology, tenant_id=tenant_id
    )

    # Update project and lifecycle state
    agent.projects[project_id]["methodology"] = new_methodology
    lifecycle_state["methodology_map"] = new_methodology_map
    lifecycle_state["current_phase"] = new_phase

    update_payload = {
        "project_id": project_id,
        "old_methodology": old_methodology,
        "new_methodology": new_methodology,
        "current_phase": new_phase,
        "methodology_map": new_methodology_map,
        "adjusted_at": datetime.now(timezone.utc).isoformat(),
    }
    workflow = DurableWorkflow(
        name="methodology_adjustment",
        tasks=[
            DurableTask(
                name="persist_methodology",
                action=lambda ctx: _persist_methodology_decision(agent, ctx),
            ),
            DurableTask(
                name="publish_methodology",
                action=lambda ctx: _publish_methodology_adjusted(agent, ctx),
            ),
            DurableTask(
                name="sync_methodology",
                action=lambda ctx: _sync_project_state(agent, ctx),
            ),
        ],
        sleep=agent.orchestrator_sleep,
    )
    context = OrchestrationContext(
        workflow_id=f"methodology-{project_id}",
        tenant_id=tenant_id,
        project_id=project_id,
        correlation_id=str(uuid.uuid4()),
        payload={"project_data": update_payload},
    )
    await agent.workflow_engine.run(workflow, context)

    return update_payload


# ---------------------------------------------------------------------------
# Workflow task functions
# ---------------------------------------------------------------------------


async def _persist_methodology_decision(
    agent: ProjectLifecycleAgent, context: OrchestrationContext
) -> dict[str, Any]:
    decision = context.results.get("methodology_decision") or context.payload.get(
        "project_data", {}
    )
    return agent.persistence.store_methodology_decision(
        context.tenant_id, context.project_id, decision
    )


async def _publish_methodology_adjusted(
    agent: ProjectLifecycleAgent, context: OrchestrationContext
) -> dict[str, Any]:
    payload = context.payload.get("project_data", {})
    await agent.event_bus.publish("methodology.adjusted", payload)
    return payload


async def _sync_project_state(
    agent: ProjectLifecycleAgent, context: OrchestrationContext
) -> dict[str, Any]:
    state = (
        context.results.get("create_records", {}).get("lifecycle_state")
        or context.payload.get("project_data")
        or context.payload
    )
    results = await agent.external_sync.sync_project_state(context.project_id, state)
    return {"sync_results": [result.__dict__ for result in results]}
