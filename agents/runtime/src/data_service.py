from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, cast

import httpx

logger = logging.getLogger("agents.runtime.data_service")

# Retryable HTTP status codes (server errors and rate-limited)
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


@dataclass
class RetryConfig:
    """Configuration for automatic retries on transient failures."""

    max_retries: int = 2
    backoff_base: float = 0.5
    backoff_max: float = 5.0


@dataclass
class DataServiceClient:
    base_url: str
    client: httpx.AsyncClient
    auth_token: str | None = None
    retry_config: RetryConfig = field(default_factory=RetryConfig)

    @classmethod
    def from_url(
        cls,
        base_url: str,
        auth_token: str | None = None,
        retry_config: RetryConfig | None = None,
        **kwargs: Any,
    ) -> DataServiceClient:
        client = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=10.0, **kwargs)
        return cls(
            base_url=base_url.rstrip("/"),
            client=client,
            auth_token=auth_token,
            retry_config=retry_config or RetryConfig(),
        )

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        tenant_id: str,
        json: Any | None = None,
    ) -> httpx.Response:
        """Execute an HTTP request with automatic retry on transient failures."""
        last_exc: Exception | None = None
        for attempt in range(1 + self.retry_config.max_retries):
            try:
                response = await self.client.request(
                    method, url, json=json, headers=self._headers(tenant_id)
                )
                if response.status_code not in _RETRYABLE_STATUS_CODES or attempt == self.retry_config.max_retries:
                    response.raise_for_status()
                    return response
                # Retryable server error – fall through to backoff
                last_exc = httpx.HTTPStatusError(
                    f"Server returned {response.status_code}",
                    request=response.request,
                    response=response,
                )
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as exc:
                last_exc = exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in _RETRYABLE_STATUS_CODES:
                    raise
                last_exc = exc

            if attempt < self.retry_config.max_retries:
                backoff = min(
                    self.retry_config.backoff_base * (2 ** attempt),
                    self.retry_config.backoff_max,
                )
                logger.warning(
                    "data_service_retry",
                    extra={"method": method, "url": url, "attempt": attempt + 1, "backoff": backoff},
                )
                await asyncio.sleep(backoff)

        # All retries exhausted
        raise last_exc  # type: ignore[misc]

    async def register_schema(
        self, name: str, schema: dict[str, Any], *, version: int | None = None, tenant_id: str
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name, "schema": schema}
        if version is not None:
            payload["version"] = version
        response = await self._request_with_retry(
            "POST", "/schemas", json=payload, tenant_id=tenant_id
        )
        return cast(dict[str, Any], response.json())

    async def list_schemas(self, *, tenant_id: str) -> list[dict[str, Any]]:
        response = await self._request_with_retry("GET", "/schemas", tenant_id=tenant_id)
        return cast(list[dict[str, Any]], response.json())

    async def list_schema_versions(
        self, schema_name: str, *, tenant_id: str
    ) -> list[dict[str, Any]]:
        response = await self._request_with_retry(
            "GET", f"/schemas/{schema_name}/versions", tenant_id=tenant_id
        )
        return cast(list[dict[str, Any]], response.json())

    async def get_latest_schema(self, schema_name: str, *, tenant_id: str) -> dict[str, Any]:
        response = await self._request_with_retry(
            "GET", f"/schemas/{schema_name}/latest", tenant_id=tenant_id
        )
        return cast(dict[str, Any], response.json())

    async def get_schema_version(
        self, schema_name: str, version: int, *, tenant_id: str
    ) -> dict[str, Any]:
        response = await self._request_with_retry(
            "GET", f"/schemas/{schema_name}/versions/{version}", tenant_id=tenant_id
        )
        return cast(dict[str, Any], response.json())

    async def store_entity(
        self,
        schema_name: str,
        data: dict[str, Any],
        *,
        tenant_id: str,
        schema_version: int | None = None,
        entity_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tenant_id": tenant_id,
            "data": data,
        }
        if schema_version is not None:
            payload["schema_version"] = schema_version
        if entity_id is not None:
            payload["entity_id"] = entity_id
        response = await self._request_with_retry(
            "POST", f"/entities/{schema_name}", json=payload, tenant_id=tenant_id
        )
        return cast(dict[str, Any], response.json())

    async def get_entity(
        self, schema_name: str, entity_id: str, *, tenant_id: str
    ) -> dict[str, Any]:
        response = await self._request_with_retry(
            "GET", f"/entities/{schema_name}/{entity_id}", tenant_id=tenant_id
        )
        return cast(dict[str, Any], response.json())

    async def close(self) -> None:
        await self.client.aclose()

    def _headers(self, tenant_id: str) -> dict[str, str]:
        headers = {"X-Tenant-ID": tenant_id}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
