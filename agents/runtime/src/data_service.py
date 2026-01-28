from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class DataServiceClient:
    base_url: str
    client: httpx.AsyncClient

    @classmethod
    def from_url(cls, base_url: str, **kwargs: Any) -> "DataServiceClient":
        client = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=10.0, **kwargs)
        return cls(base_url=base_url.rstrip("/"), client=client)

    async def register_schema(
        self, name: str, schema: dict[str, Any], *, version: int | None = None, tenant_id: str
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name, "schema": schema}
        if version is not None:
            payload["version"] = version
        response = await self.client.post(
            "/schemas", json=payload, headers=_headers(tenant_id)
        )
        response.raise_for_status()
        return response.json()

    async def store_entity(
        self,
        schema_name: str,
        data: dict[str, Any],
        *,
        tenant_id: str,
        schema_version: int | None = None,
        entity_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tenant_id": tenant_id,
            "data": data,
        }
        if schema_version is not None:
            payload["schema_version"] = schema_version
        if entity_id is not None:
            payload["entity_id"] = entity_id
        response = await self.client.post(
            f"/entities/{schema_name}", json=payload, headers=_headers(tenant_id)
        )
        response.raise_for_status()
        return response.json()

    async def get_entity(self, schema_name: str, entity_id: str, *, tenant_id: str) -> dict[str, Any]:
        response = await self.client.get(
            f"/entities/{schema_name}/{entity_id}", headers=_headers(tenant_id)
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self.client.aclose()


def _headers(tenant_id: str) -> dict[str, str]:
    return {"X-Tenant-ID": tenant_id}
