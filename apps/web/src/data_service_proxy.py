from __future__ import annotations

import os
from typing import Any

import httpx


class DataServiceClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url or os.getenv("DATA_SERVICE_URL", "http://data-service:8080")
        self.timeout = timeout
        self.transport = transport

    async def store_entity(
        self,
        schema_name: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> httpx.Response:
        return await self._request(
            "POST",
            f"/v1/entities/{schema_name}",
            headers=headers,
            json=payload,
        )

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
