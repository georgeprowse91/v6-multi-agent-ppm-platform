"""Orchestration action handlers."""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any

from response_orchestration_models import (
    AgentInvocationResult,
    OrchestrationRequest,
    OrchestrationResponse,
)
from response_orchestration_utils import aggregate_responses, build_agent_activity

if TYPE_CHECKING:
    from response_orchestration_agent import ResponseOrchestrationAgent


async def orchestrate(
    agent: ResponseOrchestrationAgent,
    request_data: dict[str, Any],
) -> dict[str, Any]:
    """Orchestrate a multi-agent workflow from a validated request dict.

    Resolves or creates an execution plan, handles approval states, executes
    agents according to the dependency graph, and aggregates the responses.
    """
    request = OrchestrationRequest.model_validate(request_data)
    routing = [entry.model_dump() for entry in request.routing]
    parameters = dict(request.parameters)
    context = request.context or {}
    correlation_id = context.get("correlation_id") or request.correlation_id or str(uuid.uuid4())
    tenant_id = context.get("tenant_id") or request.tenant_id or "unknown"

    prompt_payload = agent._build_prompt_payload(request, parameters)
    if prompt_payload:
        parameters["prompt"] = prompt_payload
        external_research = await agent._maybe_attach_external_research(
            prompt_payload, parameters=parameters, context=context
        )
        if external_research:
            parameters["external_research"] = external_research
            prompt_payload["external_research"] = external_research

    if not routing and not request.plan_id:
        return OrchestrationResponse(
            aggregated_response="No agents to invoke",
            agent_results=[],
            execution_summary={"total_agents": 0},
        ).model_dump(mode="json")

    plan = await agent._resolve_plan(request.plan_id, routing)
    agent._current_plan_context = {
        "plan_id": plan.plan_id,
        "version": plan.version,
    }

    if request.plan_updates is not None:
        plan = agent.update_pending_plan(
            plan.plan_id,
            request.plan_updates,
            actor=request.approval_actor or "orchestration-api",
        )

    if request.approval_decision == "reject":
        plan.status = "rejected"
        agent._store_plan(plan)
        await agent.event_bus.publish(
            "plan.rejected",
            {
                "plan_id": plan.plan_id,
                "version": plan.version,
                "modifications": plan.modification_history,
                "actor": request.approval_actor or "orchestration-api",
            },
        )
        return OrchestrationResponse(
            aggregated_response="Plan rejected. Execution cancelled.",
            status="rejected",
            agent_results=[],
            execution_summary={
                "total_agents": len(plan.tasks),
                "successful": 0,
                "failed": 0,
                "plan_id": plan.plan_id,
                "version": plan.version,
            },
            plan=plan.model_dump(mode="json"),
        ).model_dump(mode="json")

    if agent.require_approval and request.approval_decision != "approve":
        plan.status = "pending_approval"
        agent._store_plan(plan)
        return OrchestrationResponse(
            aggregated_response="Plan created and awaiting approval.",
            status="pending_approval",
            agent_results=[],
            execution_summary={
                "total_agents": len(plan.tasks),
                "successful": 0,
                "failed": 0,
                "plan_id": plan.plan_id,
                "version": plan.version,
            },
            plan=plan.model_dump(mode="json"),
        ).model_dump(mode="json")

    plan.status = "approved"
    agent._store_plan(plan)
    await agent.event_bus.publish(
        "plan.approved",
        {
            "plan_id": plan.plan_id,
            "version": plan.version,
            "modifications": plan.modification_history,
            "actor": request.approval_actor or "orchestration-api",
        },
    )

    # Build dependency graph
    execution_plan = await agent._build_execution_plan(
        [
            {
                "agent_id": task.agent_id,
                "action": task.action,
                "depends_on": task.dependencies,
                **task.metadata,
            }
            for task in plan.tasks
        ]
    )

    # Execute agents according to plan
    execution_start = time.time()
    results = await agent._execute_plan(
        execution_plan,
        parameters,
        correlation_id=correlation_id,
        tenant_id=tenant_id,
    )

    # Aggregate responses
    aggregated = aggregate_responses(results)
    agent_activity = build_agent_activity(results, execution_start)
    agent._emit_audit_event(
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        action="orchestration.aggregated",
        outcome="success",
        metadata={
            "agent_count": len(plan.tasks),
            "successful": len([r for r in results if r.get("success")]),
            "failed": len([r for r in results if not r.get("success")]),
            "plan_id": plan.plan_id,
            "version": plan.version,
        },
    )

    response = OrchestrationResponse(
        aggregated_response=aggregated,
        status="completed",
        agent_results=[AgentInvocationResult(**result) for result in results],
        execution_summary={
            "total_agents": len(plan.tasks),
            "successful": len([r for r in results if r.get("success")]),
            "failed": len([r for r in results if not r.get("success")]),
            "plan_id": plan.plan_id,
            "version": plan.version,
        },
        agent_activity=agent_activity,
        plan=plan.model_dump(mode="json"),
    )
    return response.model_dump(mode="json")


async def handle_plan_action(
    agent: ResponseOrchestrationAgent,
    request_data: dict[str, Any],
) -> dict[str, Any]:
    """Handle a plan-level action such as approval or rejection.

    Delegates to the main orchestrate handler so plan approval decisions
    are processed within the standard workflow.
    """
    return await orchestrate(agent, request_data)
