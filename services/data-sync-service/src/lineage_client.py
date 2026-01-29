from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class LineageClient:
    base_url: str
    tenant_id: str
    token: str | None = None
    timeout: float = 5.0

    def emit_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"X-Tenant-ID": self.tenant_id}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            response = client.post("/lineage/events", json=payload, headers=headers)
            response.raise_for_status()
            return response.json()


def get_lineage_client() -> LineageClient | None:
    base_url = os.getenv("DATA_LINEAGE_SERVICE_URL")
    if not base_url:
        return None
    tenant_id = os.getenv("DATA_LINEAGE_TENANT_ID", "dev-tenant")
    token = os.getenv("DATA_LINEAGE_SERVICE_TOKEN")
    return LineageClient(base_url=base_url.rstrip("/"), tenant_id=tenant_id, token=token)
