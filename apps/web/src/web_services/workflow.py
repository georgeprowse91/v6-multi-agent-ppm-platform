from __future__ import annotations

from typing import Any

from data_service_proxy import DataServiceClient


class WorkflowService:
    def __init__(self, data_client: DataServiceClient) -> None:
        self._data_client = data_client

    async def start_workflow(self, payload: dict[str, Any]) -> dict[str, Any]:
        schema_name = payload.get("schema_name", "workflow_runs")
        response = await self._data_client.store_entity(schema_name=schema_name, payload=payload, headers={})
        return response.json()
