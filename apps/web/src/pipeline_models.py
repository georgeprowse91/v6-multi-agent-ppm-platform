from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PipelineStage = Literal["Draft", "Review", "Approved"]
PipelineItemType = Literal["intake", "project"]
PipelinePriority = Literal["High", "Medium", "Low"]


class PipelineItem(BaseModel):
    item_id: str
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    sponsor: str = Field(min_length=1)
    priority: PipelinePriority
    type: PipelineItemType
    status: PipelineStage


class PipelineBoard(BaseModel):
    stages: list[PipelineStage]
    items: list[PipelineItem]


class PipelineItemUpdate(BaseModel):
    status: PipelineStage
