from __future__ import annotations

from typing import Any

from document_proxy import DocumentServiceClient


class DocumentService:
    def __init__(self, document_client: DocumentServiceClient) -> None:
        self._document_client = document_client

    async def list_documents(self, tenant_id: str, limit: int = 20) -> dict[str, Any]:
        response = await self._document_client.list_documents(headers={"X-Tenant-ID": tenant_id})
        payload = response.json()
        if isinstance(payload, list):
            payload = payload[:limit]
        return {"items": payload}
