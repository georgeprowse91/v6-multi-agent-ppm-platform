from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

WorkflowOperator = Literal[
    "equals",
    "not_equals",
    "greater_than",
    "less_than",
    "contains",
    "exists",
]
WorkflowStepType = Literal[
    "task",
    "decision",
    "approval",
    "notification",
    "api",
    "script",
]


class WorkflowNodeCondition(BaseModel):
    field: str = Field(min_length=1)
    operator: WorkflowOperator
    value: Any | None = None


class WorkflowNodeData(BaseModel):
    label: str = Field(min_length=1)
    trigger: str | None = None
    condition: WorkflowNodeCondition | None = None
    agent_id: str | None = None
    action: str | None = None
    connector_id: str | None = None
    step_type: WorkflowStepType = "task"


class WorkflowNodePosition(BaseModel):
    x: float
    y: float


class WorkflowNode(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    position: WorkflowNodePosition
    data: WorkflowNodeData


class WorkflowEdge(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    source: str
    target: str


class WorkflowDefinitionPayload(BaseModel):
    workflow_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str | None = None
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    definition: dict[str, Any]


class WorkflowDefinitionRecord(WorkflowDefinitionPayload):
    created_at: str
    updated_at: str


class WorkflowDefinitionSummary(BaseModel):
    workflow_id: str
    name: str
    description: str | None = None
    updated_at: str
