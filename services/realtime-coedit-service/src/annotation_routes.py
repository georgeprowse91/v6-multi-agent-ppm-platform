"""REST API routes for agent annotations in collaborative editing sessions."""

from __future__ import annotations

from typing import Any

from annotations import (
    Annotation,
    generate_suggestions,
    get_annotation_store,
)
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/sessions", tags=["annotations"])


class SuggestRequest(BaseModel):
    block_id: str
    block_content: str
    context: dict[str, Any] = Field(default_factory=dict)


@router.post("/{session_id}/annotations")
async def create_annotation(session_id: str, annotation: Annotation) -> Annotation:
    store = get_annotation_store()
    return store.create_annotation(session_id, annotation)


@router.get("/{session_id}/annotations")
async def list_annotations(session_id: str) -> list[Annotation]:
    store = get_annotation_store()
    return store.list_annotations(session_id)


@router.post("/{session_id}/annotations/{annotation_id}/dismiss")
async def dismiss_annotation(session_id: str, annotation_id: str) -> dict:
    store = get_annotation_store()
    ann = store.dismiss_annotation(annotation_id)
    return {"dismissed": ann is not None, "annotation_id": annotation_id}


@router.post("/{session_id}/annotations/{annotation_id}/apply")
async def apply_annotation(session_id: str, annotation_id: str) -> dict:
    store = get_annotation_store()
    ann = store.apply_annotation(annotation_id)
    return {"applied": ann is not None, "annotation_id": annotation_id}


@router.post("/{session_id}/annotations/suggest")
async def suggest_annotations(session_id: str, request: SuggestRequest) -> list[Annotation]:
    """Generate AI-powered annotation suggestions for a content block."""
    suggestions = await generate_suggestions(
        session_id=session_id,
        block_id=request.block_id,
        block_content=request.block_content,
        context=request.context,
    )
    # Persist the suggestions so they appear in the annotation list
    store = get_annotation_store()
    for ann in suggestions:
        store.create_annotation(session_id, ann)
    return suggestions
