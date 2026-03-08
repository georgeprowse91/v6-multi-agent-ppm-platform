from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from workflow.celery_app import celery_app
from workflow.dispatcher import WorkflowDispatcher
from workflow.executor import StepExecutionOutcome, WorkflowStepExecutor, WorkflowTaskContext

AGENT_CLIENT_OVERRIDE = None
APPROVAL_AGENT_OVERRIDE = None
_CONTEXT: WorkflowTaskContext | None = None


def _task_context() -> WorkflowTaskContext:
    global _CONTEXT
    if _CONTEXT is None:
        db_path = os.getenv("WORKFLOW_DB_PATH", "services/workflow-service/storage/workflows.db")
        _CONTEXT = WorkflowTaskContext(Path(db_path))
    if AGENT_CLIENT_OVERRIDE is not None:
        _CONTEXT.agent_client = AGENT_CLIENT_OVERRIDE
    if APPROVAL_AGENT_OVERRIDE is not None:
        _CONTEXT.approval_agent = APPROVAL_AGENT_OVERRIDE
    return _CONTEXT


def _executor() -> WorkflowStepExecutor:
    context = _task_context()
    return WorkflowStepExecutor(context.store, context.approval_agent, context.agent_client)


def _dispatch_next(outcome: StepExecutionOutcome, run_id: str, actor: dict[str, Any]) -> None:
    dispatcher = WorkflowDispatcher()
    if outcome.parallel_branches:
        for branch_id in outcome.parallel_branches:
            dispatcher.dispatch_step(run_id, branch_id, actor)
        return
    if outcome.should_retry and outcome.next_step_id:
        dispatcher.dispatch_step(
            run_id, outcome.next_step_id, actor, countdown=outcome.retry_delay_seconds
        )
    elif outcome.next_step_id:
        dispatcher.dispatch_step(run_id, outcome.next_step_id, actor)


@celery_app.task(name="workflow.execute_step")
def execute_step_task(run_id: str, step_id: str, actor: dict[str, Any]) -> dict[str, Any]:
    executor = _executor()
    outcome = executor.execute(run_id, step_id, actor)
    if outcome.should_retry:
        _dispatch_next(
            StepExecutionOutcome(
                status=outcome.status,
                next_step_id=step_id,
                should_retry=True,
                retry_delay_seconds=outcome.retry_delay_seconds,
            ),
            run_id,
            actor,
        )
    elif outcome.next_step_id:
        _dispatch_next(outcome, run_id, actor)
    return {
        "status": outcome.status,
        "next_step_id": outcome.next_step_id,
        "should_retry": outcome.should_retry,
        "retry_delay_seconds": outcome.retry_delay_seconds,
    }
