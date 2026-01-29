from __future__ import annotations

import os
from typing import Any

import httpx


class WorkflowClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url or os.getenv("WORKFLOW_ENGINE_URL", "http://workflow-engine:8080")
        if timeout is None:
            timeout = float(os.getenv("WORKFLOW_ENGINE_TIMEOUT_S", "10"))
        self.timeout = timeout
        self.transport = transport

    async def start_workflow(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        return await self._request_json("POST", "/workflows/start", headers=headers, json=payload)

    async def list_workflows(self, headers: dict[str, str]) -> list[dict[str, Any]]:
        response = await self._request_json("GET", "/workflows", headers=headers)
        return list(response)

    async def get_workflow(self, run_id: str, headers: dict[str, str]) -> dict[str, Any]:
        return await self._request_json("GET", f"/workflows/{run_id}", headers=headers)

    async def resume_workflow(self, run_id: str, headers: dict[str, str]) -> dict[str, Any]:
        return await self._request_json("POST", f"/workflows/{run_id}/resume", headers=headers)

    async def _request_json(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        json: dict[str, Any] | None = None,
    ) -> Any:
        response = await self._request(method, path, headers=headers, json=json)
        response.raise_for_status()
        return response.json()

    async def _request(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        async with httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout, transport=self.transport
        ) as client:
            return await client.request(method, path, headers=headers, json=json)
