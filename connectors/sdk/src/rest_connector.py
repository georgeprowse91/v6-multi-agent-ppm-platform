"""
Reusable REST connector base classes.

Provides common authentication, connection testing, read/write, and schema helpers
for connectors that integrate with REST APIs.
"""

from __future__ import annotations

import base64
import os
from typing import Any

from auth import OAuth2TokenManager
from base_connector import (
    BaseConnector,
    ConnectionStatus,
    ConnectionTestResult,
)
from http_client import HttpClient, HttpClientError, RetryConfig
from secrets import resolve_secret


class RestConnector(BaseConnector):
    """Base class for REST-based connectors with simple read/write behavior."""

    AUTH_TEST_ENDPOINT: str = "/"
    AUTH_TEST_PARAMS: dict[str, Any] | None = None
    RESOURCE_PATHS: dict[str, dict[str, Any]] = {}
    SCHEMA: dict[str, Any] = {}
    RATE_LIMIT_PER_MINUTE: int | None = None

    def __init__(
        self,
        config: Any,
        *,
        client: HttpClient | None = None,
        transport: Any | None = None,
    ) -> None:
        super().__init__(config)
        self._client = client
        self._transport = transport

    def _build_client(self) -> HttpClient:
        raise NotImplementedError

    def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        client = self._build_client()
        return client.request(method, url, **kwargs)

    def authenticate(self) -> bool:
        try:
            response = self._request("GET", self.AUTH_TEST_ENDPOINT, params=self.AUTH_TEST_PARAMS)
            self._authenticated = response.status_code == 200
            return self._authenticated
        except (HttpClientError, ValueError):
            self._authenticated = False
            return False

    def test_connection(self) -> ConnectionTestResult:
        try:
            response = self._request("GET", self.AUTH_TEST_ENDPOINT, params=self.AUTH_TEST_PARAMS)
            if response.status_code == 401:
                return ConnectionTestResult(
                    status=ConnectionStatus.UNAUTHORIZED,
                    message="Invalid credentials. Please verify connector settings.",
                )
            if response.status_code != 200:
                return ConnectionTestResult(
                    status=ConnectionStatus.FAILED,
                    message=f"API returned unexpected status: {response.status_code}",
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
            raise RuntimeError("Failed to authenticate with connector")
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
            items = data
            for key in items_path.split("."):
                if not isinstance(items, dict):
                    return []
                items = items.get(key, {})
            if isinstance(items, list):
                return items
            return []
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
            raise RuntimeError("Failed to authenticate with connector")
        if resource_type not in self.RESOURCE_PATHS:
            raise ValueError(f"Unsupported resource type: {resource_type}")
        info = self.RESOURCE_PATHS[resource_type]
        write_path = info.get("write_path")
        if not write_path:
            raise ValueError(f"Write not supported for resource: {resource_type}")
        method = info.get("write_method", "POST")
        response = self._request(method, write_path, json=data)
        payload = response.json()
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            return payload.get("items", [payload]) if payload else []
        return []

    def get_schema(self) -> dict[str, Any]:
        return self.SCHEMA


class ApiKeyRestConnector(RestConnector):
    """REST connector using API key authentication."""

    API_KEY_ENV: str = ""
    INSTANCE_URL_ENV: str = ""
    API_KEY_HEADER: str = "Authorization"
    API_KEY_PREFIX: str | None = None

    def _get_credentials(self) -> tuple[str, str]:
        instance_url = resolve_secret(os.getenv(self.INSTANCE_URL_ENV)) or self.config.instance_url
        api_key = resolve_secret(os.getenv(self.API_KEY_ENV))
        if not instance_url:
            raise ValueError(f"{self.INSTANCE_URL_ENV} environment variable is required")
        if not api_key:
            raise ValueError(f"{self.API_KEY_ENV} environment variable is required")
        return instance_url, api_key

    def _build_client(self) -> HttpClient:
        if self._client:
            return self._client
        instance_url, api_key = self._get_credentials()
        header_value = f"{self.API_KEY_PREFIX} {api_key}".strip() if self.API_KEY_PREFIX else api_key
        retry_config = RetryConfig(
            max_retries=3,
            backoff_factor=0.5,
            retry_statuses=(429, 500, 502, 503, 504),
        )
        self._client = HttpClient(
            base_url=instance_url,
            headers={
                "Accept": "application/json",
                self.API_KEY_HEADER: header_value,
            },
            timeout=30.0,
            rate_limit_per_minute=self.RATE_LIMIT_PER_MINUTE,
            retry_config=retry_config,
            transport=self._transport,
        )
        return self._client


class BasicAuthRestConnector(RestConnector):
    """REST connector using HTTP Basic authentication."""

    INSTANCE_URL_ENV: str = ""
    USERNAME_ENV: str = ""
    PASSWORD_ENV: str = ""

    def _get_credentials(self) -> tuple[str, str, str]:
        instance_url = resolve_secret(os.getenv(self.INSTANCE_URL_ENV)) or self.config.instance_url
        username = resolve_secret(os.getenv(self.USERNAME_ENV))
        password = resolve_secret(os.getenv(self.PASSWORD_ENV))
        if not instance_url:
            raise ValueError(f"{self.INSTANCE_URL_ENV} environment variable is required")
        if not username or not password:
            raise ValueError(
                f"{self.USERNAME_ENV} and {self.PASSWORD_ENV} environment variables are required"
            )
        return instance_url, username, password

    def _build_client(self) -> HttpClient:
        if self._client:
            return self._client
        instance_url, username, password = self._get_credentials()
        token = f"{username}:{password}".encode("utf-8")
        auth_header = base64.b64encode(token).decode("utf-8")
        retry_config = RetryConfig(
            max_retries=3,
            backoff_factor=0.5,
            retry_statuses=(429, 500, 502, 503, 504),
        )
        self._client = HttpClient(
            base_url=instance_url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {auth_header}",
            },
            timeout=30.0,
            rate_limit_per_minute=self.RATE_LIMIT_PER_MINUTE,
            retry_config=retry_config,
            transport=self._transport,
        )
        return self._client


class OAuth2RestConnector(RestConnector):
    """REST connector using OAuth2 refresh tokens."""

    INSTANCE_URL_ENV: str = ""
    CLIENT_ID_ENV: str = ""
    CLIENT_SECRET_ENV: str = ""
    REFRESH_TOKEN_ENV: str = ""
    TOKEN_URL_ENV: str = ""
    DEFAULT_TOKEN_URL: str = ""
    SCOPES_ENV: str = ""
    KEYVAULT_URL_ENV: str = "CONNECTOR_KEYVAULT_URL"
    REFRESH_TOKEN_SECRET_ENV: str = "CONNECTOR_REFRESH_TOKEN_SECRET"

    def __init__(
        self,
        config: Any,
        *,
        client: HttpClient | None = None,
        token_manager: OAuth2TokenManager | None = None,
        transport: Any | None = None,
    ) -> None:
        super().__init__(config, client=client, transport=transport)
        self._token_manager = token_manager

    def _get_credentials(self) -> tuple[str, str, str, str]:
        instance_url = resolve_secret(os.getenv(self.INSTANCE_URL_ENV)) or self.config.instance_url
        client_id = resolve_secret(os.getenv(self.CLIENT_ID_ENV))
        client_secret = resolve_secret(os.getenv(self.CLIENT_SECRET_ENV))
        refresh_token = resolve_secret(os.getenv(self.REFRESH_TOKEN_ENV))
        if not instance_url:
            raise ValueError(f"{self.INSTANCE_URL_ENV} environment variable is required")
        if not client_id or not client_secret or not refresh_token:
            raise ValueError(
                f"{self.CLIENT_ID_ENV}, {self.CLIENT_SECRET_ENV}, and {self.REFRESH_TOKEN_ENV} are required"
            )
        return instance_url, client_id, client_secret, refresh_token

    def _build_token_manager(self) -> OAuth2TokenManager:
        if self._token_manager:
            return self._token_manager
        instance_url, client_id, client_secret, refresh_token = self._get_credentials()
        token_url = resolve_secret(os.getenv(self.TOKEN_URL_ENV)) or self.DEFAULT_TOKEN_URL
        scope = resolve_secret(os.getenv(self.SCOPES_ENV)) if self.SCOPES_ENV else None
        keyvault_url = resolve_secret(os.getenv(self.KEYVAULT_URL_ENV))
        refresh_token_secret = resolve_secret(os.getenv(self.REFRESH_TOKEN_SECRET_ENV))
        self._token_manager = OAuth2TokenManager(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            scope=scope,
            keyvault_url=keyvault_url,
            refresh_token_secret_name=refresh_token_secret,
        )
        self._instance_url = instance_url
        return self._token_manager

    def _build_client(self) -> HttpClient:
        if self._client:
            return self._client
        instance_url, _, _, _ = self._get_credentials()
        token_manager = self._build_token_manager()
        retry_config = RetryConfig(
            max_retries=3,
            backoff_factor=0.5,
            retry_statuses=(429, 500, 502, 503, 504),
        )
        self._client = HttpClient(
            base_url=instance_url,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token_manager.get_access_token()}",
            },
            timeout=30.0,
            rate_limit_per_minute=self.RATE_LIMIT_PER_MINUTE,
            retry_config=retry_config,
            transport=self._transport,
        )
        return self._client

    def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        client = self._build_client()
        token_manager = self._build_token_manager()
        try:
            return client.request(method, url, **kwargs)
        except HttpClientError as exc:
            if exc.status_code != 401:
                raise
        token_manager.refresh()
        client.set_header("Authorization", f"Bearer {token_manager.get_access_token()}")
        return client.request(method, url, **kwargs)
