from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from dependencies import get_document_service_client
from web_services.documents import DocumentService

router = APIRouter(prefix="/v1/api/document-canvas", tags=["documents"])


def get_document_service() -> DocumentService:
    return DocumentService(get_document_service_client())


@router.get("/documents")
async def list_documents(
    tenant_id: str = Query(default="demo-tenant"),
    limit: int = Query(default=20, ge=1, le=100),
    service: DocumentService = Depends(get_document_service),
) -> dict:
    return await service.list_documents(tenant_id=tenant_id, limit=limit)
