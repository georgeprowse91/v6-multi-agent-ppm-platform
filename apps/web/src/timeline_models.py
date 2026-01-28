from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator
from pydantic.config import ConfigDict

TimelineStatus = Literal["planned", "at_risk", "complete"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _strip_optional(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


class MilestoneBase(BaseModel):
    title: str = Field(min_length=1)
    date: str
    status: TimelineStatus
    owner: str | None = None
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("title must be non-empty")
        return trimmed

    @field_validator("date")
    @classmethod
    def _validate_date(cls, value: str) -> str:
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("date must be YYYY-MM-DD") from exc
        return value

    @field_validator("owner", "notes")
    @classmethod
    def _normalize_optional(cls, value: str | None) -> str | None:
        return _strip_optional(value)


class MilestoneCreate(MilestoneBase):
    model_config = ConfigDict(extra="forbid")


class MilestoneUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    date: str | None = None
    status: TimelineStatus | None = None
    owner: str | None = None
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("title must be non-empty")
        return trimmed

    @field_validator("owner", "notes")
    @classmethod
    def _normalize_optional(cls, value: str | None) -> str | None:
        return _strip_optional(value)

    @field_validator("date")
    @classmethod
    def _validate_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("date must be YYYY-MM-DD") from exc
        return value


class Milestone(MilestoneBase):
    model_config = ConfigDict(extra="forbid")
    milestone_id: str
    tenant_id: str
    project_id: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def build(cls, tenant_id: str, project_id: str, payload: MilestoneCreate) -> "Milestone":
        now = utc_now()
        return cls(
            milestone_id=str(uuid4()),
            tenant_id=tenant_id,
            project_id=project_id,
            title=payload.title,
            date=payload.date,
            status=payload.status,
            owner=payload.owner,
            notes=payload.notes,
            created_at=now,
            updated_at=now,
        )


class TimelineResponse(BaseModel):
    tenant_id: str
    project_id: str
    milestones: list[Milestone]


class TimelineExportResponse(BaseModel):
    tenant_id: str
    project_id: str
    exported_at: datetime
    milestones: list[Milestone]
