from __future__ import annotations

import os
from typing import Any

import httpx


class AnalyticsServiceClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url or os.getenv(
            "ANALYTICS_SERVICE_URL", "http://analytics-service:8080"
        )
        self.timeout = timeout
        self.transport = transport

    async def get_project_health(self, project_id: str, headers: dict[str, str]) -> httpx.Response:
        return await self._request("GET", f"/api/projects/{project_id}/health", headers=headers)

    async def get_project_trends(self, project_id: str, headers: dict[str, str]) -> httpx.Response:
        return await self._request(
            "GET", f"/api/projects/{project_id}/health/trends", headers=headers
        )

    async def request_what_if(
        self, project_id: str, payload: dict[str, Any], headers: dict[str, str]
    ) -> httpx.Response:
        return await self._request(
            "POST",
            f"/api/projects/{project_id}/health/what-if",
            headers=headers,
            json=payload,
        )

    async def get_project_kpis(self, project_id: str, headers: dict[str, str]) -> httpx.Response:
        return await self._request("GET", f"/api/projects/{project_id}/kpis", headers=headers)

    async def get_project_narrative(
        self, project_id: str, headers: dict[str, str]
    ) -> httpx.Response:
        return await self._request(
            "GET", f"/api/projects/{project_id}/kpis/narrative", headers=headers
        )

    async def get_project_aggregations(
        self, project_id: str, headers: dict[str, str]
    ) -> httpx.Response:
        return await self._request(
            "GET", f"/api/projects/{project_id}/aggregations", headers=headers
        )

    async def get_powerbi_report(
        self, report_type: str, headers: dict[str, str]
    ) -> httpx.Response:
        return await self._request(
            "GET", f"/api/powerbi/reports/{report_type}", headers=headers
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
