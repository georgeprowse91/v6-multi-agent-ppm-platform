from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CertificationDocument:
    document_id: str
    filename: str
    content_type: str
    storage_path: str
    uploaded_at: str
    uploaded_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "content_type": self.content_type,
            "storage_path": self.storage_path,
            "uploaded_at": self.uploaded_at,
            "uploaded_by": self.uploaded_by,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CertificationDocument:
        return cls(
            document_id=payload["document_id"],
            filename=payload["filename"],
            content_type=payload.get("content_type", ""),
            storage_path=payload.get("storage_path", ""),
            uploaded_at=payload.get("uploaded_at", _now()),
            uploaded_by=payload.get("uploaded_by"),
        )


@dataclass
class CertificationRecord:
    connector_id: str
    tenant_id: str
    compliance_status: str
    certification_date: str | None = None
    expires_at: str | None = None
    audit_reference: str | None = None
    notes: str | None = None
    documents: list[CertificationDocument] = field(default_factory=list)
    updated_at: str = field(default_factory=_now)
    updated_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "tenant_id": self.tenant_id,
            "compliance_status": self.compliance_status,
            "certification_date": self.certification_date,
            "expires_at": self.expires_at,
            "audit_reference": self.audit_reference,
            "notes": self.notes,
            "documents": [doc.to_dict() for doc in self.documents],
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CertificationRecord:
        return cls(
            connector_id=payload["connector_id"],
            tenant_id=payload["tenant_id"],
            compliance_status=payload.get("compliance_status", "pending"),
            certification_date=payload.get("certification_date"),
            expires_at=payload.get("expires_at"),
            audit_reference=payload.get("audit_reference"),
            notes=payload.get("notes"),
            documents=[
                CertificationDocument.from_dict(doc)
                for doc in payload.get("documents", [])
            ],
            updated_at=payload.get("updated_at", _now()),
            updated_by=payload.get("updated_by"),
        )


class CertificationStore:
    def __init__(self, storage_path: Path | None = None, document_root: Path | None = None) -> None:
        self.storage_path = storage_path or Path(
            os.getenv("CERTIFICATION_STORE_PATH", "data/connectors/certifications.json")
        )
        self.document_root = document_root or Path(
            os.getenv("CERTIFICATION_DOCUMENT_ROOT", "data/connectors/certification_documents")
        )
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.document_root.mkdir(parents=True, exist_ok=True)

    def _load_all(self) -> list[dict[str, Any]]:
        if not self.storage_path.exists():
            return []
        return cast(list[dict[str, Any]], json.loads(self.storage_path.read_text()))

    def _save_all(self, records: list[dict[str, Any]]) -> None:
        self.storage_path.write_text(json.dumps(records, indent=2))

    def list_records(self, tenant_id: str) -> list[CertificationRecord]:
        return [
            CertificationRecord.from_dict(record)
            for record in self._load_all()
            if record.get("tenant_id") == tenant_id
        ]

    def get_record(self, connector_id: str, tenant_id: str) -> CertificationRecord | None:
        for record in self._load_all():
            if record.get("connector_id") == connector_id and record.get("tenant_id") == tenant_id:
                return CertificationRecord.from_dict(record)
        return None

    def upsert_record(self, record: CertificationRecord) -> CertificationRecord:
        records = self._load_all()
        updated = False
        for idx, item in enumerate(records):
            if item.get("connector_id") == record.connector_id and item.get("tenant_id") == record.tenant_id:
                records[idx] = record.to_dict()
                updated = True
                break
        if not updated:
            records.append(record.to_dict())
        self._save_all(records)
        return record

    def add_document(
        self,
        connector_id: str,
        tenant_id: str,
        filename: str,
        content_type: str,
        content: bytes,
        uploaded_by: str | None = None,
    ) -> CertificationDocument:
        doc_id = str(uuid4())
        safe_name = filename.replace("/", "_")
        connector_dir = self.document_root / connector_id
        connector_dir.mkdir(parents=True, exist_ok=True)
        file_path = connector_dir / f"{doc_id}-{safe_name}"
        file_path.write_bytes(content)
        return CertificationDocument(
            document_id=doc_id,
            filename=safe_name,
            content_type=content_type,
            storage_path=str(file_path),
            uploaded_at=_now(),
            uploaded_by=uploaded_by,
        )
