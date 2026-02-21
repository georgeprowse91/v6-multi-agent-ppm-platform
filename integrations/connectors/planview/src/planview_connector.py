"""
Planview Connector Implementation

Implements the BaseConnector interface for Planview integration.
Supports:
- OAuth2 token refresh
- Connection testing
- Reading projects
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Add SDK to path
SDK_PATH = Path(__file__).resolve().parents[2] / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))
CONNECTORS_PATH = Path(__file__).resolve().parents[2]
if str(CONNECTORS_PATH) not in sys.path:
    sys.path.insert(0, str(CONNECTORS_PATH))

from integrations.connectors.sdk.src.auth import OAuth2TokenManager
from base_connector import (
    BaseConnector,
    ConnectionStatus,
    ConnectionTestResult,
    ConnectorCategory,
    ConnectorConfig,
)
from http_client import HttpClient, HttpClientError, RetryConfig
try:
    from mcp_client.client import MCPClient
    from mcp_client.errors import (
        MCPAuthenticationError,
        MCPResponseError,
        MCPServerError,
        MCPToolNotFoundError,
        MCPTransportError,
    )
except ImportError:
    from mcp_client import (
        MCPClient,
        MCPClientError,
        MCPResponseError,
        MCPServerError,
        MCPToolNotFoundError,
        MCPTransportError,
    )
    MCPAuthenticationError = MCPClientError
try:
    from .mappers import map_from_mcp_response, map_to_mcp_params
except ImportError:
    from mappers import map_from_mcp_response, map_to_mcp_params
from secrets import fetch_keyvault_secret, resolve_secret

DEFAULT_TOKEN_URL = "https://api.planview.com/oauth2/token"

logger = logging.getLogger(__name__)


class PlanviewConnector(BaseConnector):
    """Planview connector for reading portfolio and project data."""

    CONNECTOR_ID = "planview"
    CONNECTOR_NAME = "Planview"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.PPM
    SUPPORTS_WRITE = False
    SCHEMA = {
        "portfolios": {"id": "string", "name": "string"},
        "projects": {"id": "string", "name": "string", "status": "string"},
    }

    def __init__(
        self,
        config: ConnectorConfig,
        *,
        client: HttpClient | None = None,
        token_manager: OAuth2TokenManager | None = None,
        mcp_client: MCPClient | None = None,
        transport: Any | None = None,
    ) -> None:
        super().__init__(config)
        self._client = client
        self._token_manager = token_manager
        self._mcp_client = mcp_client
        self._transport = transport
        self._instance_url: str | None = None

    def _get_credentials(self) -> tuple[str, str, str, str]:
        instance_url = resolve_secret(os.getenv("PLANVIEW_INSTANCE_URL")) or self.config.instance_url
        keyvault_url = resolve_secret(os.getenv("PLANVIEW_KEYVAULT_URL"))
        client_id = resolve_secret(os.getenv("PLANVIEW_CLIENT_ID"))
        client_secret = resolve_secret(os.getenv("PLANVIEW_CLIENT_SECRET"))
        refresh_token = resolve_secret(os.getenv("PLANVIEW_REFRESH_TOKEN"))
        client_id_secret = resolve_secret(os.getenv("PLANVIEW_CLIENT_ID_SECRET"))
        client_secret_secret = resolve_secret(os.getenv("PLANVIEW_CLIENT_SECRET_SECRET"))
        refresh_token_secret = resolve_secret(os.getenv("PLANVIEW_REFRESH_TOKEN_SECRET"))
        client_id = (
            fetch_keyvault_secret(keyvault_url, client_id_secret) if client_id_secret else client_id
        ) or client_id
        client_secret = (
            fetch_keyvault_secret(keyvault_url, client_secret_secret)
            if client_secret_secret
            else client_secret
        ) or client_secret
        refresh_token = (
            fetch_keyvault_secret(keyvault_url, refresh_token_secret)
            if refresh_token_secret
            else refresh_token
        ) or refresh_token
        if not instance_url:
            raise ValueError("PLANVIEW_INSTANCE_URL environment variable is required")
        if not client_id or not client_secret or not refresh_token:
            raise ValueError(
                "PLANVIEW_CLIENT_ID, PLANVIEW_CLIENT_SECRET, and PLANVIEW_REFRESH_TOKEN are required"
            )
        return instance_url, client_id, client_secret, refresh_token

    def _build_token_manager(self) -> OAuth2TokenManager:
        if self._token_manager:
            return self._token_manager
        instance_url, client_id, client_secret, refresh_token = self._get_credentials()
        self._instance_url = instance_url
        token_url = resolve_secret(os.getenv("PLANVIEW_TOKEN_URL")) or DEFAULT_TOKEN_URL
        scope = resolve_secret(os.getenv("PLANVIEW_SCOPES"))
        keyvault_url = resolve_secret(os.getenv("PLANVIEW_KEYVAULT_URL"))
        refresh_secret = resolve_secret(os.getenv("PLANVIEW_REFRESH_TOKEN_SECRET"))
        client_secret_secret = resolve_secret(os.getenv("PLANVIEW_CLIENT_SECRET_SECRET"))
        return OAuth2TokenManager(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            scope=scope,
            keyvault_url=keyvault_url,
            refresh_token_secret_name=refresh_secret,
            client_secret_secret_name=client_secret_secret,
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

    def _build_mcp_client(self) -> MCPClient:
        if self._mcp_client:
            return self._mcp_client
        if not self.config.mcp_server_url:
            raise ValueError("Planview MCP server URL is required")
        self._mcp_client = MCPClient(
            mcp_server_id=self.config.mcp_server_id or self.CONNECTOR_ID,
            mcp_server_url=self.config.mcp_server_url,
            config=self.config,
        )
        return self._mcp_client

    def _should_use_mcp(self, operation: str | None = None) -> bool:
        return bool(
            self.config.prefer_mcp
            and self.config.mcp_server_url
            and self.config.is_mcp_enabled_for(operation)
        )

    def _run_mcp(self, coroutine: Any) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coroutine)
        finally:
            loop.close()

    def _extract_records(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("records", "items", "values", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
        return []

    def _try_mcp_then_rest(
        self,
        *,
        operation: str,
        mcp_call: Any,
        rest_call: Any,
    ) -> Any:
        if not self._should_use_mcp(operation):
            return rest_call()
        try:
            return mcp_call()
        except (
            MCPToolNotFoundError,
            MCPAuthenticationError,
            MCPResponseError,
            MCPServerError,
            MCPTransportError,
            ValueError,
        ) as exc:
            logger.warning(
                "MCP %s failed for Planview connector; falling back to REST. Error: %s",
                operation,
                exc,
            )
            return rest_call()

    def _list_records(
        self,
        *,
        resource_type: str,
        filters: dict[str, Any] | None,
        limit: int,
        offset: int,
        rest_call: Any,
    ) -> list[dict[str, Any]]:
        def mcp_call() -> list[dict[str, Any]]:
            client = self._build_mcp_client()
            canonical_payload = {
                "resource_type": resource_type,
                "filters": filters or {},
                "limit": limit,
                "offset": offset,
            }
            params = map_to_mcp_params("list", canonical_payload)
            result = self._run_mcp(client.list_records(params))
            return map_from_mcp_response("list", result)

        return self._try_mcp_then_rest(
            operation="list",
            mcp_call=mcp_call,
            rest_call=rest_call,
        )

    def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        client = self._build_client()
        token_manager = self._build_token_manager()
        client.set_header("Authorization", f"Bearer {token_manager.get_access_token()}")
        try:
            return client.request(method, url, **kwargs)
        except HttpClientError as exc:
            if exc.status_code != 401:
                raise
        token_manager.refresh()
        client.set_header("Authorization", f"Bearer {token_manager.get_access_token()}")
        return client.request(method, url, **kwargs)

    def refresh_tokens(self) -> None:
        token_manager = self._build_token_manager()
        token_manager.refresh()
        if self._client:
            self._client.set_header("Authorization", f"Bearer {token_manager.get_access_token()}")

    def authenticate(self) -> bool:
        try:
            response = self._request("GET", "/api/v1/projects", params={"limit": 1})
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
            response = self._request("GET", "/api/v1/projects", params={"limit": 1})
            if response.status_code == 401:
                return ConnectionTestResult(
                    status=ConnectionStatus.UNAUTHORIZED,
                    message="Invalid credentials. Please check your Planview OAuth settings.",
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
                message="Successfully connected to Planview",
                details={"instance_url": self._instance_url},
            )
        except HttpClientError as exc:
            if exc.status_code == 401:
                return ConnectionTestResult(
                    status=ConnectionStatus.UNAUTHORIZED,
                    message="Invalid credentials. Please check your Planview OAuth settings.",
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
            raise RuntimeError("Failed to authenticate with Planview")
        if resource_type != "projects":
            raise ValueError(f"Unsupported resource type: {resource_type}")
        records = self._list_records(
            resource_type=resource_type,
            filters=filters,
            limit=limit,
            offset=offset,
            rest_call=lambda: self._read_projects(limit=limit, offset=offset),
        )
        return [self._normalize_project_record(record) for record in records]

    def get_schema(self) -> dict[str, Any]:
        return self.SCHEMA

    def _read_projects(self, *, limit: int, offset: int) -> list[dict[str, Any]]:
        client = self._build_client()
        projects: list[dict[str, Any]] = []

        def is_last(data: dict[str, Any], items: list[dict[str, Any]]) -> bool:
            total = data.get("total", 0)
            current_offset = data.get("offset", 0)
            return not items or current_offset + limit >= total

        for page in client.paginate_offset(
            "/api/v1/projects",
            params={"offset": offset},
            items_path="items",
            offset_param="offset",
            limit_param="limit",
            limit=limit,
            is_last_page=is_last,
        ):
            for item in page:
                projects.append(self._normalize_project_record(item))
        return projects

    def _normalize_project_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": record.get("id"),
            "program_id": record.get("program_id")
            or record.get("programId")
            or record.get("program")
            or "unassigned",
            "name": record.get("name") or record.get("title"),
            "status": record.get("status") or record.get("project_status") or "execution",
            "start_date": record.get("start_date") or record.get("startDate"),
            "end_date": record.get("end_date") or record.get("endDate"),
            "owner": record.get("owner") or record.get("owner_name"),
            "classification": record.get("classification") or "internal",
            "created_at": record.get("created_at") or record.get("createdAt"),
        }


def create_planview_connector(
    instance_url: str = "",
    sync_direction: str = "inbound",
    sync_frequency: str = "daily",
    transport: Any | None = None,
) -> PlanviewConnector:
    from base_connector import SyncDirection, SyncFrequency

    config = ConnectorConfig(
        connector_id="planview",
        name="Planview",
        category=ConnectorCategory.PPM,
        enabled=True,
        sync_direction=SyncDirection(sync_direction),
        sync_frequency=SyncFrequency(sync_frequency),
        instance_url=instance_url,
    )
    return PlanviewConnector(config, transport=transport)
