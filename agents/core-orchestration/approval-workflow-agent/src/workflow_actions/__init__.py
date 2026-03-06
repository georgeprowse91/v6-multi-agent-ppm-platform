"""
Action handlers for the Workflow Engine Agent.

Each sub-module implements one (or a small group of related) action(s).
The main ``WorkflowEngineAgent.process()`` method dispatches to these
handlers, passing ``self`` so they can access the agent's stores, queues
and event infrastructure.
"""

from workflow_actions.assign_task import handle_assign_task
from workflow_actions.cancel_workflow import handle_cancel_workflow
from workflow_actions.complete_task import handle_complete_task
from workflow_actions.define_workflow import handle_define_workflow
from workflow_actions.deploy_bpmn import handle_deploy_bpmn_workflow, handle_upload_bpmn_workflow
from workflow_actions.get_workflow_status import handle_get_workflow_status
from workflow_actions.handle_event import handle_handle_event
from workflow_actions.pause_resume_workflow import handle_pause_workflow, handle_resume_workflow
from workflow_actions.query_workflows import handle_get_task_inbox, handle_get_workflow_instances
from workflow_actions.retry_failed_task import handle_retry_failed_task
from workflow_actions.start_workflow import handle_start_workflow
from workflow_actions.worker import mark_task_failed, run_worker_once

__all__ = [
    "handle_assign_task",
    "handle_cancel_workflow",
    "handle_complete_task",
    "handle_define_workflow",
    "handle_deploy_bpmn_workflow",
    "handle_get_task_inbox",
    "handle_get_workflow_instances",
    "handle_get_workflow_status",
    "handle_handle_event",
    "handle_pause_workflow",
    "handle_resume_workflow",
    "handle_retry_failed_task",
    "handle_start_workflow",
    "handle_upload_bpmn_workflow",
    "mark_task_failed",
    "run_worker_once",
]
