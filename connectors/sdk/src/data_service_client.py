from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class DataServiceClient:
    base_url: str
    tenant_id: str
    client: httpx.Client

    @classmethod
    def from_url(cls, base_url: str, tenant_id: str, **kwargs: Any) -> "DataServiceClient":
        client = httpx.Client(base_url=base_url.rstrip("/"), timeout=10.0, **kwargs)
        return cls(base_url=base_url.rstrip("/"), tenant_id=tenant_id, client=client)

    def register_schema(self, name: str, schema: dict[str, Any], version: int | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name, "schema": schema}
        if version is not None:
            payload["version"] = version
        response = self.client.post("/schemas", json=payload, headers=self._headers())
        response.raise_for_status()
        return response.json()

    def store_entity(
        self,
        schema_name: str,
        data: dict[str, Any],
        *,
        schema_version: int | None = None,
        entity_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "data": data,
        }
        if schema_version is not None:
            payload["schema_version"] = schema_version
        if entity_id is not None:
            payload["entity_id"] = entity_id
        response = self.client.post(
            f"/entities/{schema_name}", json=payload, headers=self._headers()
        )
        response.raise_for_status()
        return response.json()

    def get_entity(self, schema_name: str, entity_id: str) -> dict[str, Any]:
        response = self.client.get(
            f"/entities/{schema_name}/{entity_id}", headers=self._headers()
        )
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self.client.close()

    def _headers(self) -> dict[str, str]:
        return {"X-Tenant-ID": self.tenant_id}
