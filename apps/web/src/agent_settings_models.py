from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class AgentRegistryEntry(BaseModel):
    agent_id: str
    name: str
    category: str
    description: str
    outputs: list[str]
    default_enabled: bool
    required: bool


class AgentSettingsEntry(BaseModel):
    agent_id: str
    enabled: bool
    config: dict[str, Any] = Field(default_factory=dict)
    updated_at: str


class ProjectAgentSettings(BaseModel):
    tenant_id: str
    project_id: str
    defaults_version: int = 1
    agents: dict[str, AgentSettingsEntry] = Field(default_factory=dict)


class AgentProjectEntry(BaseModel):
    agent_id: str
    name: str
    category: str
    description: str
    outputs: list[str]
    required: bool
    enabled: bool
    config: dict[str, Any] = Field(default_factory=dict)


class AgentConfigUpdate(BaseModel):
    enabled: bool | None = None
    config: dict[str, Any] | None = None

    @field_validator("config")
    @classmethod
    def _config_is_object(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        if not isinstance(value, dict):
            raise ValueError("config must be a JSON object")
        return value
