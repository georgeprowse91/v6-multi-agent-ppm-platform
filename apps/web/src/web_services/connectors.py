from __future__ import annotations

from connector_hub_proxy import ConnectorHubClient


class ConnectorService:
    def __init__(self, connector_client: ConnectorHubClient) -> None:
        self._connector_client = connector_client

    async def list_instances(self) -> list[dict]:
        response = await self._connector_client.list_connectors(headers={})
        payload = response.json()
        if isinstance(payload, dict):
            return payload.get("connectors", [])
        return payload
