from __future__ import annotations

import os
from typing import Any

import httpx


class OrchestratorProxyClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url or os.getenv("API_GATEWAY_URL", "http://api-gateway:8000")
        if timeout is None:
            timeout = float(os.getenv("ASSISTANT_TIMEOUT_S", "20"))
        self.timeout = timeout
        self.transport = transport

    async def send_query(
        self,
        query: str,
        context: dict[str, Any],
        headers: dict[str, str],
        prompt: dict[str, Any] | None = None,
    ) -> httpx.Response:
        payload: dict[str, Any] = {"query": query, "context": context}
        if prompt:
            payload["prompt"] = prompt
        return await self._request("POST", "/api/v1/query", headers=headers, json=payload)

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
