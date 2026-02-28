"""
Regulatory Compliance Connector

Connector for HIPAA and FDA CFR 21 Part 11 compliance APIs.
"""

from __future__ import annotations

import os
from typing import Any

from base_connector import (
    BaseConnector,
    ConnectionStatus,
    ConnectionTestResult,
    ConnectorCategory,
    ConnectorConfig,
)
from http_client import HttpClient, HttpClientError, RetryConfig
try:
    from connector_secrets import resolve_secret
except ImportError:  # pragma: no cover
    from connector_secrets import resolve_secret


class RegulatoryComplianceConnector(BaseConnector):
    CONNECTOR_ID = "regulatory_compliance"
    CONNECTOR_NAME = "Regulatory Compliance"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.COMPLIANCE
    SUPPORTS_WRITE = True

    API_KEY_ENV = "REGULATORY_COMPLIANCE_API_KEY"
    ENDPOINT_ENV = "REGULATORY_COMPLIANCE_ENDPOINT"
    AUTH_TEST_ENDPOINT = "/health"

    RESOURCE_PATHS = {
        "audit_logs": {
            "path": "/audit-logs",
            "items_path": "items",
            "write_method": "POST",
        },
        "compliance_events": {
            "path": "/events",
            "items_path": "items",
        },
    }

    def __init__(
        self,
        config: ConnectorConfig,
        *,
        client: HttpClient | None = None,
        transport: Any | None = None,
    ) -> None:
        super().__init__(config)
        self._client = client
        self._transport = transport

    def _get_endpoint(self) -> str:
        endpoint = resolve_secret(os.getenv(self.ENDPOINT_ENV))
        if not endpoint:
            endpoint = self.config.instance_url
        if not endpoint:
            endpoint = self.config.custom_fields.get("endpoint_url", "")
        if not endpoint:
            raise ValueError(f"{self.ENDPOINT_ENV} environment variable is required")
        return endpoint

    def _get_api_key(self) -> str:
        api_key = resolve_secret(os.getenv(self.API_KEY_ENV))
        if not api_key:
            api_key = str(self.config.custom_fields.get("api_key", "")).strip()
        if not api_key:
            raise ValueError(f"{self.API_KEY_ENV} environment variable is required")
        return api_key

    def _build_client(self) -> HttpClient:
        if self._client:
            return self._client
        endpoint = self._get_endpoint()
        api_key = self._get_api_key()
        retry_config = RetryConfig(
            max_retries=3,
            backoff_factor=0.5,
            retry_statuses=(429, 500, 502, 503, 504),
        )
        self._client = HttpClient(
            base_url=endpoint,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            timeout=30.0,
            retry_config=retry_config,
            transport=self._transport,
        )
        return self._client

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        client = self._build_client()
        return client.request(method, path, **kwargs)

    def authenticate(self) -> bool:
        try:
            response = self._request("GET", self.AUTH_TEST_ENDPOINT)
            self._authenticated = response.status_code == 200
            return self._authenticated
        except (HttpClientError, ValueError):
            self._authenticated = False
            return False

    def test_connection(self) -> ConnectionTestResult:
        try:
            response = self._request("GET", self.AUTH_TEST_ENDPOINT)
            if response.status_code == 401:
                return ConnectionTestResult(
                    status=ConnectionStatus.UNAUTHORIZED,
                    message="Invalid credentials. Please verify connector settings.",
                )
            if response.status_code != 200:
                return ConnectionTestResult(
                    status=ConnectionStatus.FAILED,
                    message=f"Compliance API returned unexpected status: {response.status_code}",
                    details={"status_code": response.status_code},
                )
            self._authenticated = True
            return ConnectionTestResult(
                status=ConnectionStatus.CONNECTED,
                message="Successfully connected",
            )
        except HttpClientError as exc:
            if exc.status_code == 401:
                return ConnectionTestResult(
                    status=ConnectionStatus.UNAUTHORIZED,
                    message="Invalid credentials. Please verify connector settings.",
                )
            return ConnectionTestResult(
                status=ConnectionStatus.FAILED,
                message=f"Connection failed: {exc.message}",
                details={"status_code": exc.status_code},
            )
        except ValueError as exc:
            return ConnectionTestResult(
                status=ConnectionStatus.INVALID_CONFIG,
                message=str(exc),
            )
        except Exception as exc:  # pragma: no cover - defensive
            return ConnectionTestResult(
                status=ConnectionStatus.FAILED,
                message=f"Unexpected error: {exc}",
            )

    def read(
        self,
        resource_type: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if not self._authenticated and not self.authenticate():
            raise RuntimeError("Failed to authenticate with compliance API")
        if resource_type not in self.RESOURCE_PATHS:
            raise ValueError(f"Unsupported resource type: {resource_type}")
        info = self.RESOURCE_PATHS[resource_type]
        params = {"limit": limit, "offset": offset}
        if filters:
            params.update(filters)
        response = self._request("GET", info["path"], params=params)
        data = response.json()
        items_path = info.get("items_path")
        if items_path:
            items: Any = data
            for key in items_path.split("."):
                if not isinstance(items, dict):
                    return []
                items = items.get(key, {})
            return items if isinstance(items, list) else []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("items", []) if isinstance(data.get("items"), list) else [data]
        return []

    def write(
        self,
        resource_type: str,
        data: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not self.SUPPORTS_WRITE:
            raise NotImplementedError(
                f"{self.CONNECTOR_NAME} does not support write operations"
            )
        if not self._authenticated and not self.authenticate():
            raise RuntimeError("Failed to authenticate with compliance API")
        if resource_type not in self.RESOURCE_PATHS:
            raise ValueError(f"Unsupported resource type: {resource_type}")
        info = self.RESOURCE_PATHS[resource_type]
        write_method = info.get("write_method")
        if not write_method:
            raise ValueError(f"Write not supported for resource: {resource_type}")
        response = self._request(write_method, info["path"], json=data)
        payload = response.json()
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            return payload.get("items", [payload]) if payload else []
        return []
