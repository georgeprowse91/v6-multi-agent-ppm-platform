from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MergeRecord(BaseModel):
    record_id: str
    source_system: str
    summary: str
    attributes: dict[str, Any]
    last_updated: str | None = None


class MergePreview(BaseModel):
    summary: str
    attributes: dict[str, Any]


class MergeDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    reviewer_id: str
    comments: str | None = None


class MergeDecisionRecord(MergeDecision):
    decided_at: str


class MergeReviewCase(BaseModel):
    case_id: str
    entity_type: str
    status: Literal["pending", "approved", "rejected"] = "pending"
    similarity_score: float
    rationale: str
    primary_record: MergeRecord
    duplicate_record: MergeRecord
    merge_preview: MergePreview
    created_at: str
    updated_at: str
    decision: MergeDecisionRecord | None = None
