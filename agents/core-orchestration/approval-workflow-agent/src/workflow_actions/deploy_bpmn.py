"""Action handlers: deploy_bpmn_workflow, upload_bpmn_workflow."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from workflow_engine_agent import WorkflowEngineAgent


async def handle_deploy_bpmn_workflow(
    agent: WorkflowEngineAgent,
    tenant_id: str,
    bpmn_xml: str,
    workflow_name: str | None = None,
) -> dict[str, Any]:
    from workflow_actions.define_workflow import handle_define_workflow

    workflow_config = {
        "name": workflow_name or "BPMN Workflow",
        "description": "BPMN 2.0 deployment",
        "bpmn_xml": bpmn_xml,
        "definition_source": "bpmn_upload",
    }
    result = await handle_define_workflow(agent, tenant_id, workflow_config)
    return {
        "workflow_id": result.get("workflow_id"),
        "status": result.get("status"),
        "tasks": result.get("tasks"),
        "definition_source": "bpmn_upload",
    }


async def handle_upload_bpmn_workflow(
    agent: WorkflowEngineAgent,
    tenant_id: str,
    bpmn_xml: str | None,
    bpmn_path: str | None,
    workflow_name: str | None = None,
) -> dict[str, Any]:
    if not bpmn_xml and bpmn_path:
        bpmn_xml = Path(bpmn_path).read_text(encoding="utf-8")
    if not bpmn_xml:
        raise ValueError("BPMN XML payload is required")
    return await handle_deploy_bpmn_workflow(agent, tenant_id, bpmn_xml, workflow_name)
