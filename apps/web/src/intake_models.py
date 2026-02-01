from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, EmailStr, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IntakeSponsorDetails(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    department: str = Field(min_length=1)
    title: str | None = None


class IntakeBusinessCase(BaseModel):
    summary: str = Field(min_length=1)
    justification: str = Field(min_length=1)
    expected_benefits: str = Field(min_length=1)
    estimated_budget: str | None = None


class IntakeSuccessCriteria(BaseModel):
    metrics: str = Field(min_length=1)
    target_date: str | None = None
    risks: str | None = None


class IntakeAttachments(BaseModel):
    summary: str = Field(min_length=1)
    links: list[str] = Field(default_factory=list)


class IntakeRequestCreate(BaseModel):
    sponsor: IntakeSponsorDetails
    business_case: IntakeBusinessCase
    success_criteria: IntakeSuccessCriteria
    attachments: IntakeAttachments
    reviewers: list[str] = Field(default_factory=list)


class IntakeDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    reviewer_id: str = Field(min_length=1)
    comments: str | None = None


class IntakeDecisionRecord(BaseModel):
    decision: Literal["approved", "rejected"]
    reviewer_id: str
    comments: str | None = None
    decided_at: datetime


class IntakeRequest(BaseModel):
    request_id: str
    status: Literal["pending", "approved", "rejected"]
    created_at: datetime
    updated_at: datetime
    sponsor: IntakeSponsorDetails
    business_case: IntakeBusinessCase
    success_criteria: IntakeSuccessCriteria
    attachments: IntakeAttachments
    reviewers: list[str]
    decision: IntakeDecisionRecord | None = None

    @classmethod
    def build(cls, payload: IntakeRequestCreate) -> "IntakeRequest":
        timestamp = utc_now()
        return cls(
            request_id=str(uuid4()),
            status="pending",
            created_at=timestamp,
            updated_at=timestamp,
            sponsor=payload.sponsor,
            business_case=payload.business_case,
            success_criteria=payload.success_criteria,
            attachments=payload.attachments,
            reviewers=payload.reviewers,
        )
