"""Pipeline board routes."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException

from routes._deps import PipelineBoard, PipelineItem, PipelineItemUpdate, pipeline_store

router = APIRouter()


@router.get("/api/pipeline/{entity_type}/{entity_id}", response_model=PipelineBoard)
def get_pipeline_board(
    entity_type: Literal["portfolio", "program"], entity_id: str
) -> PipelineBoard:
    return pipeline_store.get_board(entity_type, entity_id)


@router.patch(
    "/api/pipeline/{entity_type}/{entity_id}/items/{item_id}", response_model=PipelineItem
)
def update_pipeline_item(
    entity_type: Literal["portfolio", "program"],
    entity_id: str,
    item_id: str,
    payload: PipelineItemUpdate,
) -> PipelineItem:
    try:
        item = pipeline_store.update_item_status(entity_type, entity_id, item_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not item:
        raise HTTPException(status_code=404, detail="Pipeline item not found")
    return item
