"""Action handler: define_workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from engine_utils import (
    build_durable_orchestration,
    generate_workflow_id,
    normalize_workflow_definition,
    parse_workflow_definition,
    validate_workflow_definition,
)
from workflow_spec import WorkflowSpecError

if TYPE_CHECKING:
    from workflow_engine_agent import WorkflowEngineAgent


async def handle_define_workflow(
    agent: WorkflowEngineAgent, tenant_id: str, workflow_config: dict[str, Any]
) -> dict[str, Any]:
    """
    Define new workflow process.

    Returns workflow ID and validation.
    """
    agent.logger.info("Defining workflow: %s", workflow_config.get("name"))

    normalized = normalize_workflow_definition(workflow_config)
    workflow_id = normalized.get("workflow_id") or await generate_workflow_id()

    # Validate workflow definition
    validation = await validate_workflow_definition(normalized)

    if not validation.get("valid"):
        return {"workflow_id": None, "status": "invalid", "errors": validation.get("errors")}

    # Parse workflow definition
    try:
        parsed_workflow = await parse_workflow_definition(normalized)
    except WorkflowSpecError as exc:
        return {"workflow_id": None, "status": "invalid", "errors": [str(exc)]}
    durable_orchestration = build_durable_orchestration(
        workflow_id,
        parsed_workflow.get("tasks", []),
        parsed_workflow.get("transitions", []),
        normalized.get("definition_source", "inline"),
    )

    # Create workflow definition
    workflow = {
        "workflow_id": workflow_id,
        "name": normalized.get("name"),
        "description": normalized.get("description"),
        "version": normalized.get("version", 1),
        "tasks": parsed_workflow.get("tasks", []),
        "events": parsed_workflow.get("events", []),
        "gateways": parsed_workflow.get("gateways", []),
        "transitions": parsed_workflow.get("transitions", []),
        "variables": normalized.get("variables", {}),
        "orchestration": durable_orchestration,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": normalized.get("author"),
        "definition_source": normalized.get("definition_source", "inline"),
        "task_sequence": [task.get("task_id") for task in parsed_workflow.get("tasks", [])],
        "dependencies": parsed_workflow.get("dependencies", {}),
    }

    # Store workflow definition (use tenant_id:workflow_id to avoid cross-tenant cache collisions)
    agent.workflow_definitions[f"{tenant_id}:{workflow_id}"] = workflow
    await agent.state_store.save_definition(tenant_id, workflow_id, workflow.copy())
    agent.durable_orchestrations[workflow_id] = {
        "workflow_id": workflow_id,
        "definition": workflow,
        "steps": durable_orchestration.get("steps", []),
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }

    await agent._register_event_triggers(
        tenant_id, workflow_id, normalized.get("event_triggers", [])
    )
    await agent._emit_workflow_event(
        tenant_id,
        "workflow.defined",
        {"workflow_id": workflow_id, "name": workflow.get("name")},
    )

    return {
        "workflow_id": workflow_id,
        "name": workflow["name"],
        "version": workflow["version"],
        "tasks": len(workflow["tasks"]),
        "orchestration": durable_orchestration,
        "status": "defined",
    }
