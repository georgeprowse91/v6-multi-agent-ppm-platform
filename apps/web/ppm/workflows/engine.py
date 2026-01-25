from __future__ import annotations

from typing import Any

from ..agents.registry import run_agent
from ..store import Store
from ..utils import now_iso


def start_workflow(store: Store, *, def_id: str, entity_id: str, actor: str) -> str:
    wf = store.get_workflow_def(def_id)
    if not wf:
        raise KeyError(f"Workflow def not found: {def_id}")
    steps = wf["def"].get("steps", [])
    if not steps:
        raise ValueError("Workflow has no steps")

    first_step_id = steps[0]["id"]
    context = {"history": [], "started_by": actor, "started_at": now_iso()}
    instance_id = store.create_workflow_instance(
        def_id=def_id,
        entity_id=entity_id,
        status="InProgress",
        current_step_id=first_step_id,
        context=context,
    )
    store.log_event(
        actor=actor,
        event_type="workflow_started",
        entity_id=entity_id,
        details={"instance_id": instance_id, "def_id": def_id},
    )
    return instance_id


def _get_step(wf_def: dict[str, Any], step_id: str) -> dict[str, Any]:
    for s in wf_def.get("steps", []):
        if s.get("id") == step_id:
            return s
    raise KeyError(f"Step not found: {step_id}")


def advance_workflow(
    store: Store,
    *,
    instance_id: str,
    actor: str,
    approve: bool | None = None,
    agent_inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    inst = store.get_workflow_instance(instance_id)
    if not inst:
        raise KeyError(f"Workflow instance not found: {instance_id}")

    wf = store.get_workflow_def(inst["def_id"])
    if not wf:
        raise KeyError(f"Workflow def not found: {inst['def_id']}")
    wf_def = wf["def"]

    current_step_id = inst.get("current_step_id")
    if not current_step_id:
        return {"status": inst["status"], "message": "No current step"}

    step = _get_step(wf_def, current_step_id)
    ctx = inst.get("context") or {}
    history = ctx.get("history") or []

    result: dict[str, Any] = {
        "instance_id": instance_id,
        "step_id": current_step_id,
        "step_name": step.get("name"),
    }

    if step.get("terminal"):
        store.update_workflow_instance(
            instance_id,
            status="Completed",
            current_step_id=None,
            context={**ctx, "history": history},
        )
        return {**result, "status": "Completed"}

    if step.get("gate"):
        if approve is None:
            return {
                **result,
                "status": "AwaitingApproval",
                "message": "This step is an approval gate; provide approve=True/False.",
            }
        next_id = (step.get("next_on_approve") if approve else step.get("next_on_reject")) or []
        next_step_id = next_id[0] if isinstance(next_id, list) and next_id else None
        history.append(
            {
                "step_id": current_step_id,
                "type": "gate",
                "approved": approve,
                "actor": actor,
                "timestamp": now_iso(),
            }
        )
        store.update_workflow_instance(
            instance_id, current_step_id=next_step_id, context={**ctx, "history": history}
        )
        store.log_event(
            actor=actor,
            event_type="workflow_gate_decision",
            entity_id=inst["entity_id"],
            details={
                "instance_id": instance_id,
                "step_id": current_step_id,
                "approved": approve,
            },
        )
        return {**result, "gate": True, "approved": approve, "next_step_id": next_step_id}

    # Non-gate step: run agent
    agent_id = int(step.get("agent_id") or 0)
    inputs = agent_inputs or {}
    agent_out = {}
    if agent_id and agent_id not in (1, 2, 3):
        agent_out = run_agent(
            store, agent_id=agent_id, actor=actor, entity_id=inst["entity_id"], inputs=inputs
        )

    next_list = step.get("next") or []
    next_step_id = next_list[0] if isinstance(next_list, list) and next_list else None

    history.append(
        {
            "step_id": current_step_id,
            "type": "agent",
            "agent_id": agent_id,
            "actor": actor,
            "timestamp": now_iso(),
            "outputs": agent_out,
        }
    )
    store.update_workflow_instance(
        instance_id, current_step_id=next_step_id, context={**ctx, "history": history}
    )
    store.log_event(
        actor=actor,
        event_type="workflow_step_completed",
        entity_id=inst["entity_id"],
        details={
            "instance_id": instance_id,
            "step_id": current_step_id,
            "agent_id": agent_id,
        },
    )

    # If the next step is terminal, auto-mark completed when we reach it is left to UI/action.
    return {**result, "agent_id": agent_id, "agent_out": agent_out, "next_step_id": next_step_id}
