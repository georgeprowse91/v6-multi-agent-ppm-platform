from __future__ import annotations

import os

import httpx


class LineageServiceClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url or os.getenv(
            "DATA_LINEAGE_SERVICE_URL", "http://data-lineage-service:8080"
        )
        self.timeout = timeout
        self.transport = transport

    async def get_quality_summary(self, headers: dict[str, str]) -> httpx.Response:
        return await self._request("GET", "/quality/summary", headers=headers)

    async def _request(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        json: dict[str, object] | None = None,
    ) -> httpx.Response:
        async with httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout, transport=self.transport
        ) as client:
            return await client.request(method, path, headers=headers, json=json)
