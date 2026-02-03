from __future__ import annotations

import os
from typing import Any, cast

import httpx


class WorkflowClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        fallback_url = os.getenv("WORKFLOW_ENGINE_URL")
        self.base_url = base_url or fallback_url or "http://workflow-engine:8080"
        if timeout is None:
            timeout = float(os.getenv("WORKFLOW_ENGINE_TIMEOUT_S", "10"))
        self.timeout: float = timeout
        self.transport: httpx.AsyncBaseTransport | None = transport

    async def start_workflow(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        response = await self._request_json(
            "POST",
            "/v1/workflows/start",
            headers=headers,
            json=payload,
        )
        return cast(dict[str, Any], response)

    async def list_workflows(self, headers: dict[str, str]) -> list[dict[str, Any]]:
        response = await self._request_json("GET", "/v1/workflows", headers=headers)
        return cast(list[dict[str, Any]], response)

    async def get_workflow(self, run_id: str, headers: dict[str, str]) -> dict[str, Any]:
        response = await self._request_json("GET", f"/v1/workflows/{run_id}", headers=headers)
        return cast(dict[str, Any], response)

    async def resume_workflow(self, run_id: str, headers: dict[str, str]) -> dict[str, Any]:
        response = await self._request_json(
            "POST",
            f"/v1/workflows/{run_id}/resume",
            headers=headers,
        )
        return cast(dict[str, Any], response)

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
