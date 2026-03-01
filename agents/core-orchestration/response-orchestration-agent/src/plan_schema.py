from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PlanTask(BaseModel):
    model_config = ConfigDict(extra="allow")

    task_id: str
    agent_id: str
    action: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Plan(BaseModel):
    model_config = ConfigDict(extra="allow")

    plan_id: str
    tasks: list[PlanTask]
    status: str = "pending_approval"
    modification_history: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = Field(ge=1)

    def apply_task_updates(self, tasks: list[dict[str, Any]], *, actor: str = "system") -> None:
        self.tasks = [PlanTask.model_validate(task) for task in tasks]
        self.modification_history.append(
            {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "actor": actor,
                "task_count": len(self.tasks),
            }
        )
