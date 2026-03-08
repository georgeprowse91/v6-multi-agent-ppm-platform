"""Knowledge documents and lessons-learned routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from routes._deps import (
    _autonomous_deliverables_enabled,
    _get_knowledge_store,
    _session_from_request,
    build_event,
    get_audit_log_store,
)
from routes._models import (
    DocumentSummaryResponse,
    DocumentVersionRequest,
    DocumentVersionResponse,
    LessonRecommendationRequest,
    LessonRequest,
    LessonResponse,
)

router = APIRouter()


@router.post("/api/knowledge/documents", response_model=DocumentVersionResponse)
async def create_document_version(
    payload: DocumentVersionRequest, request: Request
) -> DocumentVersionResponse:
    store = _get_knowledge_store()
    record = store.create_document_version(
        project_id=payload.project_id,
        document_key=payload.document_key,
        name=payload.name,
        doc_type=payload.doc_type,
        classification=payload.classification,
        status=payload.status,
        content=payload.content,
        metadata=payload.metadata,
        track_edits=_autonomous_deliverables_enabled(),
    )
    if payload.status.lower() == "published":
        session = _session_from_request(request) or {}
        get_audit_log_store().record_event(
            build_event(
                tenant_id=session.get("tenant_id", "unknown"),
                actor_id=session.get("subject") or "ui-user",
                actor_type="user",
                roles=session.get("roles") or [],
                action="document.published",
                resource_type="document",
                resource_id=record.document_id,
                outcome="success",
                metadata={"project_id": record.project_id},
            )
        )
    return DocumentVersionResponse(
        document_id=record.document_id,
        document_key=record.document_key,
        project_id=record.project_id,
        name=record.name,
        doc_type=record.doc_type,
        classification=record.classification,
        version=record.version,
        status=record.status,
        content=record.content,
        created_at=record.created_at.isoformat(),
        metadata=record.metadata,
    )


@router.get("/api/knowledge/documents", response_model=list[DocumentSummaryResponse])
async def list_documents(
    project_id: str | None = None, query: str | None = None
) -> list[DocumentSummaryResponse]:
    store = _get_knowledge_store()
    records = store.list_documents(project_id=project_id, query=query)
    return [
        DocumentSummaryResponse(
            document_id=r.document_id,
            document_key=r.document_key,
            project_id=r.project_id,
            name=r.name,
            doc_type=r.doc_type,
            classification=r.classification,
            latest_version=r.latest_version,
            latest_status=r.latest_status,
            created_at=r.created_at.isoformat(),
            updated_at=r.updated_at.isoformat(),
        )
        for r in records
    ]


@router.get(
    "/api/knowledge/documents/{document_id}/versions", response_model=list[DocumentVersionResponse]
)
async def list_document_versions(document_id: str) -> list[DocumentVersionResponse]:
    store = _get_knowledge_store()
    records = store.list_versions(document_id=document_id)
    return [
        DocumentVersionResponse(
            document_id=r.document_id,
            document_key=r.document_key,
            project_id=r.project_id,
            name=r.name,
            doc_type=r.doc_type,
            classification=r.classification,
            version=r.version,
            status=r.status,
            content=r.content,
            created_at=r.created_at.isoformat(),
            metadata=r.metadata,
        )
        for r in records
    ]


@router.post("/api/knowledge/lessons", response_model=LessonResponse)
async def create_lesson(payload: LessonRequest) -> LessonResponse:
    store = _get_knowledge_store()
    r = store.create_lesson(
        project_id=payload.project_id,
        stage_id=payload.stage_id,
        stage_name=payload.stage_name,
        title=payload.title,
        description=payload.description,
        tags=payload.tags,
        topics=payload.topics,
    )
    return LessonResponse(
        lesson_id=r.lesson_id,
        project_id=r.project_id,
        stage_id=r.stage_id,
        stage_name=r.stage_name,
        title=r.title,
        description=r.description,
        tags=r.tags,
        topics=r.topics,
        created_at=r.created_at.isoformat(),
        updated_at=r.updated_at.isoformat(),
    )


@router.put("/api/knowledge/lessons/{lesson_id}", response_model=LessonResponse)
async def update_lesson(lesson_id: str, payload: LessonRequest) -> LessonResponse:
    store = _get_knowledge_store()
    r = store.update_lesson(
        lesson_id=lesson_id,
        title=payload.title,
        description=payload.description,
        tags=payload.tags,
        topics=payload.topics,
        stage_id=payload.stage_id,
        stage_name=payload.stage_name,
    )
    if not r:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return LessonResponse(
        lesson_id=r.lesson_id,
        project_id=r.project_id,
        stage_id=r.stage_id,
        stage_name=r.stage_name,
        title=r.title,
        description=r.description,
        tags=r.tags,
        topics=r.topics,
        created_at=r.created_at.isoformat(),
        updated_at=r.updated_at.isoformat(),
    )


@router.delete("/api/knowledge/lessons/{lesson_id}")
async def delete_lesson(lesson_id: str) -> dict[str, Any]:
    store = _get_knowledge_store()
    deleted = store.delete_lesson(lesson_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return {"status": "deleted", "lesson_id": lesson_id}


@router.get("/api/knowledge/lessons", response_model=list[LessonResponse])
async def list_lessons(
    project_id: str | None = None,
    query: str | None = None,
    tags: str | None = None,
    topics: str | None = None,
) -> list[LessonResponse]:
    store = _get_knowledge_store()
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    topic_list = [t.strip() for t in topics.split(",")] if topics else None
    records = store.list_lessons(
        project_id=project_id,
        query=query,
        tags=[t for t in (tag_list or []) if t],
        topics=[t for t in (topic_list or []) if t],
    )
    return [
        LessonResponse(
            lesson_id=r.lesson_id,
            project_id=r.project_id,
            stage_id=r.stage_id,
            stage_name=r.stage_name,
            title=r.title,
            description=r.description,
            tags=r.tags,
            topics=r.topics,
            created_at=r.created_at.isoformat(),
            updated_at=r.updated_at.isoformat(),
        )
        for r in records
    ]


@router.post("/api/knowledge/lessons/recommendations", response_model=list[LessonResponse])
async def recommend_lessons(payload: LessonRecommendationRequest) -> list[LessonResponse]:
    store = _get_knowledge_store()
    records = store.recommend_lessons(
        project_id=payload.project_id, tags=payload.tags, topics=payload.topics, limit=payload.limit
    )
    return [
        LessonResponse(
            lesson_id=r.lesson_id,
            project_id=r.project_id,
            stage_id=r.stage_id,
            stage_name=r.stage_name,
            title=r.title,
            description=r.description,
            tags=r.tags,
            topics=r.topics,
            created_at=r.created_at.isoformat(),
            updated_at=r.updated_at.isoformat(),
        )
        for r in records
    ]
