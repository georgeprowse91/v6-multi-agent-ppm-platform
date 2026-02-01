from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from api.certification_storage import CertificationRecord, CertificationStore, _now

router = APIRouter()

_store: CertificationStore | None = None


def _get_store() -> CertificationStore:
    global _store
    if _store is None:
        _store = CertificationStore()
    return _store


CertificationStatus = Literal["certified", "pending", "expired", "not_certified"]


class CertificationDocumentResponse(BaseModel):
    document_id: str
    filename: str
    content_type: str
    uploaded_at: str
    uploaded_by: str | None = None


class CertificationRecordResponse(BaseModel):
    connector_id: str
    tenant_id: str
    compliance_status: CertificationStatus
    certification_date: str | None = None
    expires_at: str | None = None
    audit_reference: str | None = None
    notes: str | None = None
    documents: list[CertificationDocumentResponse] = Field(default_factory=list)
    updated_at: str
    updated_by: str | None = None


class CertificationCreateRequest(BaseModel):
    connector_id: str
    compliance_status: CertificationStatus
    certification_date: str | None = None
    expires_at: str | None = None
    audit_reference: str | None = None
    notes: str | None = None
    updated_by: str | None = None


class CertificationUpdateRequest(BaseModel):
    compliance_status: CertificationStatus | None = None
    certification_date: str | None = None
    expires_at: str | None = None
    audit_reference: str | None = None
    notes: str | None = None
    updated_by: str | None = None


def _to_response(record: CertificationRecord) -> CertificationRecordResponse:
    return CertificationRecordResponse(
        connector_id=record.connector_id,
        tenant_id=record.tenant_id,
        compliance_status=record.compliance_status,
        certification_date=record.certification_date,
        expires_at=record.expires_at,
        audit_reference=record.audit_reference,
        notes=record.notes,
        documents=[
            CertificationDocumentResponse(
                document_id=doc.document_id,
                filename=doc.filename,
                content_type=doc.content_type,
                uploaded_at=doc.uploaded_at,
                uploaded_by=doc.uploaded_by,
            )
            for doc in record.documents
        ],
        updated_at=record.updated_at,
        updated_by=record.updated_by,
    )


@router.get("/certifications", response_model=list[CertificationRecordResponse])
async def list_certifications(
    http_request: Request, connector_id: str | None = None
) -> list[CertificationRecordResponse]:
    auth = http_request.state.auth
    records = _get_store().list_records(auth.tenant_id)
    if connector_id:
        records = [record for record in records if record.connector_id == connector_id]
    return [_to_response(record) for record in records]


@router.get("/certifications/{connector_id}", response_model=CertificationRecordResponse)
async def get_certification(connector_id: str, http_request: Request) -> CertificationRecordResponse:
    auth = http_request.state.auth
    record = _get_store().get_record(connector_id, auth.tenant_id)
    if not record:
        raise HTTPException(status_code=404, detail="Certification record not found")
    return _to_response(record)


@router.post("/certifications", response_model=CertificationRecordResponse)
async def create_certification(
    request: CertificationCreateRequest, http_request: Request
) -> CertificationRecordResponse:
    auth = http_request.state.auth
    record = CertificationRecord(
        connector_id=request.connector_id,
        tenant_id=auth.tenant_id,
        compliance_status=request.compliance_status,
        certification_date=request.certification_date,
        expires_at=request.expires_at,
        audit_reference=request.audit_reference,
        notes=request.notes,
        updated_by=request.updated_by or auth.subject,
    )
    _get_store().upsert_record(record)
    return _to_response(record)


@router.put("/certifications/{connector_id}", response_model=CertificationRecordResponse)
async def update_certification(
    connector_id: str, request: CertificationUpdateRequest, http_request: Request
) -> CertificationRecordResponse:
    auth = http_request.state.auth
    existing = _get_store().get_record(connector_id, auth.tenant_id)
    if not existing:
        existing = CertificationRecord(
            connector_id=connector_id,
            tenant_id=auth.tenant_id,
            compliance_status=request.compliance_status or "pending",
        )
    record = CertificationRecord(
        connector_id=connector_id,
        tenant_id=auth.tenant_id,
        compliance_status=request.compliance_status or existing.compliance_status,
        certification_date=request.certification_date or existing.certification_date,
        expires_at=request.expires_at or existing.expires_at,
        audit_reference=request.audit_reference or existing.audit_reference,
        notes=request.notes or existing.notes,
        documents=existing.documents,
        updated_by=request.updated_by or auth.subject,
    )
    _get_store().upsert_record(record)
    return _to_response(record)


@router.post("/certifications/{connector_id}/documents", response_model=CertificationRecordResponse)
async def upload_certification_document(
    connector_id: str,
    http_request: Request,
    file: UploadFile = File(...),
    uploaded_by: str | None = Form(None),
) -> CertificationRecordResponse:
    auth = http_request.state.auth
    store = _get_store()
    record = store.get_record(connector_id, auth.tenant_id)
    if not record:
        record = CertificationRecord(
            connector_id=connector_id,
            tenant_id=auth.tenant_id,
            compliance_status="pending",
        )
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty evidence document")
    document = store.add_document(
        connector_id=connector_id,
        tenant_id=auth.tenant_id,
        filename=file.filename or "evidence",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        uploaded_by=uploaded_by or auth.subject,
    )
    record.documents.append(document)
    record.updated_by = uploaded_by or auth.subject
    record.updated_at = _now()
    store.upsert_record(record)
    return _to_response(record)
