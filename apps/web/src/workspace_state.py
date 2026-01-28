from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from pydantic.config import ConfigDict

CanvasTab = Literal["document", "tree", "timeline", "spreadsheet", "dashboard"]


def _utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


class WorkspaceState(BaseModel):
    version: int = 1
    tenant_id: str
    project_id: str
    methodology: str | None = None
    current_stage_id: str | None = None
    current_activity_id: str | None = None
    activity_completion: dict[str, bool] = Field(default_factory=dict)
    current_canvas_tab: CanvasTab = "document"
    updated_at: str


class WorkspaceSelectionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str | None = None
    current_stage_id: str | None = None
    current_activity_id: str | None = None
    current_canvas_tab: CanvasTab
    methodology: str | None = None

    @field_validator("methodology")
    @classmethod
    def _non_empty_methodology(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Methodology must be non-empty when provided")
        return value


class ActivityCompletionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    activity_id: str = Field(min_length=1)
    completed: bool


def build_default_state(tenant_id: str, project_id: str) -> WorkspaceState:
    return WorkspaceState(
        tenant_id=tenant_id,
        project_id=project_id,
        methodology=None,
        current_stage_id=None,
        current_activity_id=None,
        activity_completion={},
        current_canvas_tab="document",
        updated_at=_utc_now(),
    )


def refresh_timestamp(state: WorkspaceState) -> WorkspaceState:
    return state.model_copy(update={"updated_at": _utc_now()})
