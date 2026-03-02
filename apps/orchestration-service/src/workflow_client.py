from __future__ import annotations

import os
from typing import Any, cast

import httpx
from common.resilience import ResilienceMiddleware, dependency_config_from_env


class WorkflowClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        max_retries: int | None = None,
        retry_backoff_s: float | None = None,
    ) -> None:
        fallback_url = os.getenv("WORKFLOW_SERVICE_URL")
        self.base_url = base_url or fallback_url or "http://workflow-service:8080"
        if timeout is None:
            timeout = float(os.getenv("WORKFLOW_SERVICE_TIMEOUT_S", "10"))
        self.timeout: float = timeout
        self.transport: httpx.AsyncBaseTransport | None = transport
        if max_retries is None:
            max_retries = int(os.getenv("WORKFLOW_SERVICE_MAX_RETRIES", "2"))
        if retry_backoff_s is None:
            retry_backoff_s = float(os.getenv("WORKFLOW_SERVICE_RETRY_BACKOFF_S", "0.5"))
        self.middleware = ResilienceMiddleware(
            dependency_config_from_env(
                "workflow_service",
                timeout_s=self.timeout,
                max_attempts=max_retries + 1,
                initial_backoff_s=retry_backoff_s,
            )
        )

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

            async def _operation() -> httpx.Response:
                response = await client.request(method, path, headers=headers, json=json)
                if response.status_code in {429, 502, 503, 504}:
                    raise httpx.HTTPStatusError(
                        "retryable upstream failure",
                        request=response.request,
                        response=response,
                    )
                return response

            return await self.middleware.execute_async(_operation)
