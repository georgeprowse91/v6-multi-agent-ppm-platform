"""Response Orchestration Agent - Pydantic data models and schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RoutingEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    agent_id: str
    priority: float | None = Field(default=None, ge=0.0, le=1.0)
    intent: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    action: str | None = None


class OrchestrationRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    routing: list[RoutingEntry]
    intents: list[dict[str, Any]] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    query: str | None = None
    context: dict[str, Any] | None = None
    correlation_id: str | None = None
    tenant_id: str | None = None
    prompt_id: str | None = None
    prompt_description: str | None = None
    prompt_tags: list[str] = Field(default_factory=list)
    plan_id: str | None = None
    approval_decision: str | None = None
    plan_updates: list[dict[str, Any]] | None = None
    approval_actor: str | None = None


class AgentInvocationResult(BaseModel):
    success: bool
    agent_id: str
    data: dict[str, Any] | None = None
    error: str | None = None
    cached: bool = False


class OrchestrationResponse(BaseModel):
    aggregated_response: str | dict[str, Any]
    status: str = "completed"
    agent_results: list[AgentInvocationResult]
    execution_summary: dict[str, Any]
    agent_activity: list[dict[str, Any]] = Field(default_factory=list)
    plan: dict[str, Any] | None = None


class ValidationErrorPayload(BaseModel):
    error: str
    details: list[dict[str, Any]]
