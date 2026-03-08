from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(REPO_ROOT)

from agent_client import AgentClient, get_agent_client  # noqa: E402
from approval_workflow_agent import ApprovalWorkflowAgent  # noqa: E402
from workflow_definitions import load_definition  # noqa: E402
from workflow_runtime import WorkflowRuntime  # noqa: E402
from workflow_storage import WorkflowStore  # noqa: E402


def _run_async(coro: Any) -> Any:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        return asyncio.run_coroutine_threadsafe(coro, loop).result()
    return asyncio.run(coro)


@dataclass
class StepExecutionOutcome:
    status: str
    next_step_id: str | None
    should_retry: bool
    retry_delay_seconds: int
    parallel_branches: list[str] | None = None
    join_step_id: str | None = None


class WorkflowStepExecutor:
    def __init__(
        self,
        store: WorkflowStore,
        approval_agent: ApprovalWorkflowAgent,
        agent_client: AgentClient | None,
    ) -> None:
        self.store = store
        self.runtime = WorkflowRuntime(store, approval_agent, agent_client)

    def execute(self, run_id: str, step_id: str, actor: dict[str, Any]) -> StepExecutionOutcome:
        instance = self.store.get(run_id)
        if not instance:
            raise ValueError(f"Workflow run {run_id} not found")
        definition_record = self.store.get_definition(instance.workflow_id)
        if not definition_record:
            definition = self._load_definition(instance.workflow_id)
            self.store.upsert_definition(instance.workflow_id, definition)
            definition_record = self.store.get_definition(instance.workflow_id)
        if not definition_record:
            raise ValueError("Workflow definition missing")
        result = _run_async(
            self.runtime.execute_step(instance, definition_record.definition, actor, step_id)
        )
        return StepExecutionOutcome(
            status=result.status,
            next_step_id=result.next_step_id,
            should_retry=result.should_retry,
            retry_delay_seconds=result.retry_delay_seconds,
            parallel_branches=result.parallel_branches,
            join_step_id=result.join_step_id,
        )

    def compensation_journal(self, run_id: str) -> list[dict[str, Any]]:
        return list(_run_async(self.runtime.inspect_compensation(run_id)))

    def retry_compensation(
        self, run_id: str, actor: dict[str, Any], step_id: str | None = None
    ) -> Any:
        instance = self.store.get(run_id)
        if not instance:
            raise ValueError(f"Workflow run {run_id} not found")
        definition_record = self.store.get_definition(instance.workflow_id)
        if not definition_record:
            definition = self._load_definition(instance.workflow_id)
            self.store.upsert_definition(instance.workflow_id, definition)
            definition_record = self.store.get_definition(instance.workflow_id)
        if not definition_record:
            raise ValueError("Workflow definition missing")
        return _run_async(
            self.runtime.retry_compensation(
                instance, definition_record.definition, actor, step_id=step_id
            )
        )

    def _load_definition(self, workflow_id: str) -> dict[str, Any]:
        workflow_root = REPO_ROOT / "services" / "workflow-service"
        definition_path = (
            workflow_root / "workflows" / "definitions" / f"{workflow_id}.workflow.yaml"
        )
        schema_path = workflow_root / "workflows" / "schema" / "workflow.schema.json"
        return dict(load_definition(definition_path, schema_path))


class WorkflowTaskContext:
    def __init__(self, db_path: Path) -> None:
        self.store = WorkflowStore(db_path)
        self.agent_client: AgentClient | None = get_agent_client()
        self.approval_agent = ApprovalWorkflowAgent()
        _run_async(self.approval_agent.initialize())

    def executor(self) -> WorkflowStepExecutor:
        return WorkflowStepExecutor(self.store, self.approval_agent, self.agent_client)
