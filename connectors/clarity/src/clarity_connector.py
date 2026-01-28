"""
Clarity Connector Implementation

Implements the BaseConnector interface for Clarity PPM integration.
Supports:
- OAuth2 token refresh
- Connection testing
- Reading projects
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Add SDK to path
SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from auth import OAuth2TokenManager
from base_connector import (
    BaseConnector,
    ConnectionStatus,
    ConnectionTestResult,
    ConnectorCategory,
    ConnectorConfig,
)
from http_client import HttpClient, HttpClientError, RetryConfig
from secrets import resolve_secret

DEFAULT_TOKEN_URL = "https://clarity.example.com/oauth/token"


class ClarityConnector(BaseConnector):
    """Clarity connector for reading portfolio and project data."""

    CONNECTOR_ID = "clarity"
    CONNECTOR_NAME = "Clarity PPM"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.PPM
    SUPPORTS_WRITE = False

    def __init__(
        self,
        config: ConnectorConfig,
        *,
        client: HttpClient | None = None,
        token_manager: OAuth2TokenManager | None = None,
        transport: Any | None = None,
    ) -> None:
        super().__init__(config)
        self._client = client
        self._token_manager = token_manager
        self._transport = transport
        self._instance_url: str | None = None

    def _get_credentials(self) -> tuple[str, str, str, str]:
        instance_url = resolve_secret(os.getenv("CLARITY_INSTANCE_URL")) or self.config.instance_url
        client_id = resolve_secret(os.getenv("CLARITY_CLIENT_ID"))
        client_secret = resolve_secret(os.getenv("CLARITY_CLIENT_SECRET"))
        refresh_token = resolve_secret(os.getenv("CLARITY_REFRESH_TOKEN"))
        if not instance_url:
            raise ValueError("CLARITY_INSTANCE_URL environment variable is required")
        if not client_id or not client_secret or not refresh_token:
            raise ValueError(
                "CLARITY_CLIENT_ID, CLARITY_CLIENT_SECRET, and CLARITY_REFRESH_TOKEN are required"
            )
        return instance_url, client_id, client_secret, refresh_token

    def _build_token_manager(self) -> OAuth2TokenManager:
        if self._token_manager:
            return self._token_manager
        instance_url, client_id, client_secret, refresh_token = self._get_credentials()
        self._instance_url = instance_url
        token_url = resolve_secret(os.getenv("CLARITY_TOKEN_URL")) or DEFAULT_TOKEN_URL
        scope = resolve_secret(os.getenv("CLARITY_SCOPES"))
        return OAuth2TokenManager(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            scope=scope,
        )

    def _build_client(self) -> HttpClient:
        if self._client:
            return self._client
        instance_url, _, _, _ = self._get_credentials()
        self._instance_url = instance_url
        token_manager = self._build_token_manager()
        retry_config = RetryConfig(
            max_retries=3,
            backoff_factor=0.5,
            retry_statuses=(429, 500, 502, 503, 504),
        )
        client = HttpClient(
            base_url=instance_url,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token_manager.get_access_token()}",
            },
            timeout=30.0,
            rate_limit_per_minute=600,
            retry_config=retry_config,
            transport=self._transport,
        )
        self._client = client
        return client

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

    def authenticate(self) -> bool:
        try:
            response = self._request("GET", "/ppm/rest/v1/projects", params={"limit": 1})
            if response.status_code == 200:
                self._authenticated = True
                return True
            self._authenticated = False
            return False
        except (HttpClientError, ValueError):
            self._authenticated = False
            return False

    def test_connection(self) -> ConnectionTestResult:
        try:
            response = self._request("GET", "/ppm/rest/v1/projects", params={"limit": 1})
            if response.status_code == 401:
                return ConnectionTestResult(
                    status=ConnectionStatus.UNAUTHORIZED,
                    message="Invalid credentials. Please check your Clarity OAuth settings.",
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
                message="Successfully connected to Clarity",
                details={"instance_url": self._instance_url},
            )
        except HttpClientError as exc:
            if exc.status_code == 401:
                return ConnectionTestResult(
                    status=ConnectionStatus.UNAUTHORIZED,
                    message="Invalid credentials. Please check your Clarity OAuth settings.",
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
        except Exception as exc:
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
            raise RuntimeError("Failed to authenticate with Clarity")
        if resource_type != "projects":
            raise ValueError(f"Unsupported resource type: {resource_type}")
        return self._read_projects(limit=limit, offset=offset)

    def _read_projects(self, *, limit: int, offset: int) -> list[dict[str, Any]]:
        client = self._build_client()
        projects: list[dict[str, Any]] = []

        def is_last(data: dict[str, Any], items: list[dict[str, Any]]) -> bool:
            total = data.get("total", 0)
            current_offset = data.get("offset", 0)
            return not items or current_offset + limit >= total

        for page in client.paginate_offset(
            "/ppm/rest/v1/projects",
            params={"offset": offset},
            items_path="items",
            offset_param="offset",
            limit_param="limit",
            limit=limit,
            is_last_page=is_last,
        ):
            for item in page:
                projects.append(
                    {
                        "id": item.get("id"),
                        "program_id": item.get("programId") or "unassigned",
                        "name": item.get("name"),
                        "status": item.get("status") or "execution",
                        "start_date": item.get("startDate"),
                        "end_date": item.get("finishDate"),
                        "owner": item.get("manager"),
                        "classification": item.get("classification") or "internal",
                        "created_at": item.get("createdDate"),
                    }
                )
        return projects


def create_clarity_connector(
    instance_url: str = "",
    sync_direction: str = "inbound",
    sync_frequency: str = "daily",
    transport: Any | None = None,
) -> ClarityConnector:
    from base_connector import SyncDirection, SyncFrequency

    config = ConnectorConfig(
        connector_id="clarity",
        name="Clarity PPM",
        category=ConnectorCategory.PPM,
        enabled=True,
        sync_direction=SyncDirection(sync_direction),
        sync_frequency=SyncFrequency(sync_frequency),
        instance_url=instance_url,
    )
    return ClarityConnector(config, transport=transport)
