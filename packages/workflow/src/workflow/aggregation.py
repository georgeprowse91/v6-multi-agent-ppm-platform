from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
_COMMON_SRC = REPO_ROOT / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402
ensure_monorepo_paths(REPO_ROOT)

from workflow_storage import WorkflowStore  # noqa: E402


@dataclass
class WorkflowResultAggregator:
    store: WorkflowStore

    def aggregate(self, run_id: str) -> dict[str, Any]:
        instance = self.store.get(run_id)
        if not instance:
            raise ValueError(f"Workflow run {run_id} not found")
        steps = []
        for step in self.store.list_step_states(run_id):
            steps.append(
                {
                    "step_id": step.step_id,
                    "status": step.status,
                    "attempts": step.attempts,
                    "started_at": step.started_at,
                    "completed_at": step.completed_at,
                    "error": step.error,
                    "output": step.output,
                }
            )
        events = [
            {
                "event_id": event.event_id,
                "step_id": event.step_id,
                "status": event.status,
                "message": event.message,
                "created_at": event.created_at,
            }
            for event in self.store.list_events(run_id)
        ]
        return {
            "run_id": instance.run_id,
            "workflow_id": instance.workflow_id,
            "tenant_id": instance.tenant_id,
            "status": instance.status,
            "current_step_id": instance.current_step_id,
            "payload": instance.payload,
            "created_at": instance.created_at,
            "updated_at": instance.updated_at,
            "steps": steps,
            "events": events,
        }
