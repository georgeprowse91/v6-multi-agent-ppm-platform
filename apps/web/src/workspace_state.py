from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.config import ConfigDict

CanvasTab = Literal[
    "document",
    "tree",
    "timeline",
    "spreadsheet",
    "dashboard",
    "board",
    "backlog",
    "gantt",
    "grid",
    "financial",
    "dependency_map",
    "roadmap",
    "approval",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat() + "Z"


class WorkspaceState(BaseModel):
    version: int = 1
    tenant_id: str
    project_id: str
    methodology: str | None = None
    current_stage_id: str | None = None
    current_activity_id: str | None = None
    activity_completion: dict[str, bool] = Field(default_factory=dict)
    current_canvas_tab: CanvasTab = "document"
    last_opened_document_id: str | None = None
    last_opened_sheet_id: str | None = None
    last_opened_milestone_id: str | None = None
    updated_at: str


class OpenRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str | None = None
    sheet_id: str | None = None
    milestone_id: str | None = None

    @model_validator(mode="after")
    def _ensure_single_target(self) -> OpenRef:
        provided = [
            value for value in (self.document_id, self.sheet_id, self.milestone_id) if value
        ]
        if not provided:
            raise ValueError("open_ref requires at least one id")
        if len(provided) > 1:
            raise ValueError("open_ref must target a single artifact")
        return self


class WorkspaceSelectionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str | None = None
    current_stage_id: str | None = None
    current_activity_id: str | None = None
    current_canvas_tab: CanvasTab
    methodology: str | None = None
    open_ref: OpenRef | None = None

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
        last_opened_document_id=None,
        last_opened_sheet_id=None,
        last_opened_milestone_id=None,
        updated_at=_utc_now(),
    )


def refresh_timestamp(state: WorkspaceState) -> WorkspaceState:
    return state.model_copy(update={"updated_at": _utc_now()})
