"""Intent Router Agent - Pydantic data models and schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IntentRouterContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    tenant_id: str | None = None
    correlation_id: str | None = None


class IntentRouterRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    query: str = Field(..., min_length=1)
    context: dict[str, Any] | None = None

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("query must not be empty")
        return cleaned


class IntentPrediction(BaseModel):
    intent: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class IntentRouterLLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intents: list[IntentPrediction] = Field(..., min_length=1)
    parameters: dict[str, Any] | None = None
    dependencies: dict[str, list[str]] | None = None


class IntentRouteConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str
    action: str | None = None
    dependencies: list[str] = Field(default_factory=list)


class IntentDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    min_confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    routes: list[IntentRouteConfig] = Field(default_factory=list)
    description: str | None = None


class IntentRoutingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    intents: list[IntentDefinition]
    fallback_intent: str = "general_query"
    default_min_confidence: float = Field(default=0.6, ge=0.0, le=1.0)


class ExtractedParameters(BaseModel):
    model_config = ConfigDict(extra="allow")

    project_id: str | None = None
    portfolio_id: str | None = None
    currency: str | None = None
    amount: float | None = Field(default=None, ge=0.0)
    entity_type: str | None = None
    schedule_focus: str | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        currency = value.upper()
        allowed = {"AUD", "EUR", "GBP", "JPY"}
        if currency not in allowed:
            raise ValueError("Unsupported currency")
        return currency


class RoutingDecision(BaseModel):
    agent_id: str
    priority: float = Field(..., ge=0.0, le=1.0)
    intent: str
    depends_on: list[str] = Field(default_factory=list)
    action: str | None = None


class IntentRouterResponse(BaseModel):
    intents: list[IntentPrediction]
    routing: list[RoutingDecision]
    parameters: dict[str, Any]
    query: str
    context: dict[str, Any]
    prompt_version: int | None = None


class ValidationErrorPayload(BaseModel):
    error: str
    details: list[dict[str, Any]]
