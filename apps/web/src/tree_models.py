from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.config import ConfigDict


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _strip_optional(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


class NodeType(StrEnum):
    folder = "folder"
    document = "document"
    sheet = "sheet"
    milestone = "milestone"
    note = "note"


class TreeNodeRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str | None = None
    sheet_id: str | None = None
    milestone_id: str | None = None
    text: str | None = None

    @field_validator("document_id", "sheet_id", "milestone_id", "text")
    @classmethod
    def _strip_values(cls, value: str | None) -> str | None:
        return _strip_optional(value)


def _ref_keys(ref: TreeNodeRef | None) -> set[str]:
    if ref is None:
        return set()
    return {key for key, value in ref.model_dump().items() if value is not None}


def validate_ref_for_type(node_type: NodeType, ref: TreeNodeRef | None) -> TreeNodeRef | None:
    keys = _ref_keys(ref)
    if node_type == NodeType.folder:
        if keys:
            raise ValueError("folder nodes cannot define ref")
        return None
    if node_type == NodeType.document:
        if keys != {"document_id"}:
            raise ValueError("document nodes require ref.document_id")
        return ref
    if node_type == NodeType.sheet:
        if keys != {"sheet_id"}:
            raise ValueError("sheet nodes require ref.sheet_id")
        return ref
    if node_type == NodeType.milestone:
        if keys != {"milestone_id"}:
            raise ValueError("milestone nodes require ref.milestone_id")
        return ref
    if node_type == NodeType.note:
        if not keys:
            return None
        if keys != {"text"} or not ref or not ref.text:
            raise ValueError("note nodes require ref.text when provided")
        return ref
    raise ValueError("unsupported node type")


class TreeNodeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_id: str | None = None
    type: NodeType
    title: str = Field(min_length=1)
    ref: TreeNodeRef | None = None
    sort_order: int = 0

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("title must be non-empty")
        return trimmed

    @model_validator(mode="after")
    def _validate_ref(self) -> TreeNodeCreate:
        validate_ref_for_type(self.type, self.ref)
        return self


class TreeNodeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    ref: TreeNodeRef | None = None
    sort_order: int | None = None

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("title must be non-empty")
        return trimmed


class TreeMoveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_parent_id: str | None = None
    new_sort_order: int | None = None


class TreeNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    tenant_id: str
    project_id: str
    parent_id: str | None = None
    type: NodeType
    title: str
    ref: TreeNodeRef | None = None
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _validate_ref(self) -> TreeNode:
        validate_ref_for_type(self.type, self.ref)
        return self

    @classmethod
    def build(
        cls,
        tenant_id: str,
        project_id: str,
        payload: TreeNodeCreate,
    ) -> TreeNode:
        now = utc_now()
        return cls(
            node_id=str(uuid4()),
            tenant_id=tenant_id,
            project_id=project_id,
            parent_id=payload.parent_id,
            type=payload.type,
            title=payload.title,
            ref=payload.ref,
            sort_order=payload.sort_order,
            created_at=now,
            updated_at=now,
        )


class TreeListResponse(BaseModel):
    tenant_id: str
    project_id: str
    nodes: list[TreeNode]


class TreeExportResponse(BaseModel):
    tenant_id: str
    project_id: str
    exported_at: datetime
    nodes: list[TreeNode]


class TreeDeleteResult(BaseModel):
    deleted: bool
    deleted_count: int = 0
