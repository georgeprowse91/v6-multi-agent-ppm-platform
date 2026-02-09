"""Shared agent request/response models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentContext(BaseModel):
    """Standard context payload shared across agents."""

    model_config = ConfigDict(extra="allow")

    correlation_id: str | None = None
    tenant_id: str | None = None
    user_id: str | None = None


class AgentRequest(BaseModel):
    """Standard agent request wrapper."""

    model_config = ConfigDict(extra="allow")

    context: AgentContext | None = None
    correlation_id: str | None = None
    tenant_id: str | None = None
    policy_bundle: dict[str, Any] | None = None


class AgentPayload(BaseModel):
    """Typed agent payload envelope for arbitrary response data."""

    model_config = ConfigDict(extra="allow")


class AgentResponseMetadata(BaseModel):
    """Standard agent response metadata."""

    agent_id: str
    catalog_id: str
    timestamp: str
    correlation_id: str
    trace_id: str | None = None
    execution_time_seconds: float | None = None
    policy_reasons: tuple[str, ...] | None = None


class AgentResponse(BaseModel):
    """Standard agent response contract."""

    success: bool
    data: AgentPayload | None = None
    error: str | None = None
    metadata: AgentResponseMetadata


class AgentValidationError(BaseModel):
    """Standard validation error payload."""

    error: str
    details: list[dict[str, Any]] = Field(default_factory=list)


class AgentRunStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    canceled = "canceled"


class AgentRun(BaseModel):
    """Track the lifecycle of an agent run."""

    model_config = ConfigDict(extra="allow")

    id: str
    tenant_id: str
    agent_id: str
    status: AgentRunStatus = AgentRunStatus.queued
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    delay_reason: str | None = None
    completion_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def transition_to(
        self,
        new_status: AgentRunStatus,
        *,
        timestamp: datetime | None = None,
        metadata_update: dict[str, Any] | None = None,
        delay_reason: str | None = None,
        completion_reason: str | None = None,
    ) -> AgentRun:
        transitions: dict[AgentRunStatus, set[AgentRunStatus]] = {
            AgentRunStatus.queued: {AgentRunStatus.running, AgentRunStatus.canceled},
            AgentRunStatus.running: {
                AgentRunStatus.succeeded,
                AgentRunStatus.failed,
                AgentRunStatus.canceled,
            },
            AgentRunStatus.succeeded: set(),
            AgentRunStatus.failed: set(),
            AgentRunStatus.canceled: set(),
        }
        if new_status == self.status:
            return self
        allowed = transitions.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(f"Invalid transition from {self.status} to {new_status}")

        transition_time = (timestamp or datetime.now(timezone.utc)).isoformat()
        updated_fields: dict[str, Any] = {
            "status": new_status,
            "updated_at": transition_time,
        }
        if new_status == AgentRunStatus.running and not self.started_at:
            updated_fields["started_at"] = transition_time
        if new_status in {AgentRunStatus.succeeded, AgentRunStatus.failed, AgentRunStatus.canceled}:
            updated_fields["completed_at"] = transition_time
            if completion_reason is not None:
                updated_fields["completion_reason"] = completion_reason
        if delay_reason is not None:
            updated_fields["delay_reason"] = delay_reason
        if metadata_update:
            updated_fields["metadata"] = {**self.metadata, **metadata_update}
        return self.model_copy(update=updated_fields)
