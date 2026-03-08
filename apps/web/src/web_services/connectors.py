from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
from connector_hub_proxy import ConnectorHubClient

# connectors.json is generated from manifest.yaml files by connectors/registry/generate.py
_REGISTRY_PATH = Path(__file__).resolve().parents[4] / "connectors" / "registry" / "connectors.json"


class ConnectorService:
    def __init__(
        self, connector_client: ConnectorHubClient, headers: dict[str, str] | None = None
    ) -> None:
        self._client = connector_client
        self._headers = headers or {}

    def list_types(self) -> list[dict[str, Any]]:
        """Load the connector type catalog (generated from manifests)."""
        if not _REGISTRY_PATH.exists():
            return []
        try:
            with _REGISTRY_PATH.open("r", encoding="utf-8") as f:
                payload = json.load(f)
        except (OSError, json.JSONDecodeError):
            return []
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            return list(payload.get("connectors", []))
        return []

    async def list_instances(self) -> list[dict]:
        response = await self._client.list_connectors(headers=self._headers)
        payload = response.json()
        if isinstance(payload, dict):
            return payload.get("connectors", [])
        return payload

    async def list_instances_raw(self) -> httpx.Response:
        """Return the raw response from the connector hub."""
        return await self._client.list_connectors(headers=self._headers)

    async def create_instance(self, connector_request: dict[str, Any]) -> httpx.Response:
        return await self._client.create_connector(connector_request, headers=self._headers)

    async def update_instance(self, connector_id: str, payload: dict[str, Any]) -> httpx.Response:
        return await self._client.update_connector(connector_id, payload, headers=self._headers)

    async def get_health(self, connector_id: str) -> httpx.Response:
        return await self._client.get_connector_health(connector_id, headers=self._headers)
