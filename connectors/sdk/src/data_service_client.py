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

    def register_schema(
        self, name: str, schema: dict[str, Any], version: int | None = None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name, "schema": schema}
        if version is not None:
            payload["version"] = version
        response = self.client.post("/schemas", json=payload, headers=self._headers())
        response.raise_for_status()
        return response.json()

    def list_schemas(self) -> list[dict[str, Any]]:
        response = self.client.get("/schemas", headers=self._headers())
        response.raise_for_status()
        return response.json()

    def list_schema_versions(self, schema_name: str) -> list[dict[str, Any]]:
        response = self.client.get(f"/schemas/{schema_name}/versions", headers=self._headers())
        response.raise_for_status()
        return response.json()

    def get_latest_schema(self, schema_name: str) -> dict[str, Any]:
        response = self.client.get(f"/schemas/{schema_name}/latest", headers=self._headers())
        response.raise_for_status()
        return response.json()

    def get_schema_version(self, schema_name: str, version: int) -> dict[str, Any]:
        response = self.client.get(
            f"/schemas/{schema_name}/versions/{version}", headers=self._headers()
        )
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
        response = self.client.post(f"/entities/{schema_name}", json=payload, headers=self._headers())
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


@dataclass
class DataLineageClient:
    base_url: str
    tenant_id: str
    client: httpx.Client

    @classmethod
    def from_url(cls, base_url: str, tenant_id: str, **kwargs: Any) -> "DataLineageClient":
        client = httpx.Client(base_url=base_url.rstrip("/"), timeout=10.0, **kwargs)
        return cls(base_url=base_url.rstrip("/"), tenant_id=tenant_id, client=client)

    def close(self) -> None:
        self.client.close()


class LineageEventEmitter:
    def __init__(
        self,
        connector_name: str,
        *,
        client: DataLineageClient | None = None,
        base_url: str | None = None,
        tenant_id: str | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        if client is None:
            if not base_url or not tenant_id:
                raise ValueError("base_url and tenant_id are required when client is not provided")
            http_client = http_client or httpx.Client(base_url=base_url.rstrip("/"), timeout=10.0)
            client = DataLineageClient(
                base_url=base_url.rstrip("/"),
                tenant_id=tenant_id,
                client=http_client,
            )
        self.client = client
        self.connector_name = connector_name

    def emit_event(
        self,
        *,
        source: dict[str, Any],
        target: dict[str, Any],
        transformations: list[str],
        entity_type: str | None = None,
        entity_payload: dict[str, Any] | None = None,
        quality: dict[str, Any] | None = None,
        classification: str = "internal",
        metadata: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tenant_id": self.client.tenant_id,
            "connector": self.connector_name,
            "source": source,
            "target": target,
            "transformations": transformations,
            "classification": classification,
        }
        if entity_type is not None:
            payload["entity_type"] = entity_type
        if entity_payload is not None:
            payload["entity_payload"] = entity_payload
        if quality is not None:
            payload["quality"] = quality
        if metadata is not None:
            payload["metadata"] = metadata
        if timestamp is not None:
            payload["timestamp"] = timestamp
        response = self.client.client.post(
            "/lineage/events", json=payload, headers=self._headers()
        )
        response.raise_for_status()
        return response.json()

    def _headers(self) -> dict[str, str]:
        return {"X-Tenant-ID": self.client.tenant_id}
