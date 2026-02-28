"""
Clarity Connector Implementation

Implements the BaseConnector interface for Clarity PPM integration.
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

_REPO_ROOT = Path(__file__).resolve().parents[4]
_COMMON_SRC = _REPO_ROOT / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(_REPO_ROOT)

from integrations.connectors.sdk.src.auth import OAuth2TokenManager  # noqa: E402
from base_connector import (  # noqa: E402
    BaseConnector,
    ConnectionStatus,
    ConnectionTestResult,
    ConnectorCategory,
    ConnectorConfig,
)
from http_client import HttpClient, HttpClientError, RetryConfig  # noqa: E402
from mcp_client import MCPClient, MCPClientError  # noqa: E402
from connector_secrets import fetch_keyvault_secret, resolve_secret  # noqa: E402
try:
    from .mappers import map_from_mcp_response, map_to_mcp_params
except ImportError:
    from mappers import map_from_mcp_response, map_to_mcp_params

DEFAULT_TOKEN_URL = "https://clarity.example.com/oauth/token"

logger = logging.getLogger(__name__)


class ClarityConnector(BaseConnector):
    """Clarity connector for reading portfolio and project data."""

    CONNECTOR_ID = "clarity"
    CONNECTOR_NAME = "Clarity PPM"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.PPM
    SUPPORTS_WRITE = False
    SCHEMA = {
        "projects": {"id": "string", "name": "string", "status": "string"},
    }

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
        self._mcp_client: MCPClient | None = None
        self._mcp_tool_map = {
            "list_projects": "clarity.listProjects",
            "create_project": "clarity.createProject",
            **(config.mcp_tool_map or {}),
        }

    def _get_credentials(self) -> tuple[str, str, str, str]:
        instance_url = resolve_secret(os.getenv("CLARITY_INSTANCE_URL")) or self.config.instance_url
        keyvault_url = resolve_secret(os.getenv("CLARITY_KEYVAULT_URL"))
        client_id = resolve_secret(os.getenv("CLARITY_CLIENT_ID"))
        client_secret = resolve_secret(os.getenv("CLARITY_CLIENT_SECRET"))
        refresh_token = resolve_secret(os.getenv("CLARITY_REFRESH_TOKEN"))
        client_id_secret = resolve_secret(os.getenv("CLARITY_CLIENT_ID_SECRET"))
        client_secret_secret = resolve_secret(os.getenv("CLARITY_CLIENT_SECRET_SECRET"))
        refresh_token_secret = resolve_secret(os.getenv("CLARITY_REFRESH_TOKEN_SECRET"))
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
        keyvault_url = resolve_secret(os.getenv("CLARITY_KEYVAULT_URL"))
        refresh_secret = resolve_secret(os.getenv("CLARITY_REFRESH_TOKEN_SECRET"))
        client_secret_secret = resolve_secret(os.getenv("CLARITY_CLIENT_SECRET_SECRET"))
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
            raise ValueError("Clarity MCP server URL is required")
        self._mcp_client = MCPClient(
            mcp_server_id=self.config.mcp_server_id or self.CONNECTOR_ID,
            mcp_server_url=self.config.mcp_server_url,
            config=self.config,
        )
        return self._mcp_client

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

    def _should_use_mcp(self, tool_key: str) -> bool:
        if not self.config.prefer_mcp:
            return False
        if not self.config.mcp_server_url:
            return False
        if not self.config.is_mcp_enabled_for(tool_key):
            return False
        return True

    def _normalize_project_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": record.get("id"),
            "program_id": record.get("program_id")
            or record.get("programId")
            or record.get("program")
            or "unassigned",
            "name": record.get("name"),
            "status": record.get("status") or "execution",
            "start_date": record.get("start_date") or record.get("startDate"),
            "end_date": record.get("end_date") or record.get("finishDate"),
            "owner": record.get("owner") or record.get("manager"),
            "classification": record.get("classification") or "internal",
            "created_at": record.get("created_at") or record.get("createdDate"),
        }

    def _list_projects_via_mcp(
        self,
        *,
        filters: dict[str, Any] | None,
        limit: int,
        offset: int,
        rest_call: Any,
    ) -> list[dict[str, Any]]:
        tool_key = "list_projects"
        tool_name = self._mcp_tool_map.get(tool_key)
        if not self._should_use_mcp(tool_key):
            return rest_call()
        if not tool_name:
            logger.warning(
                "MCP tool mapping missing for %s; falling back to REST for Clarity.",
                tool_key,
            )
            return rest_call()
        params = map_to_mcp_params(
            "list",
            {
                "resource_type": "projects",
                "filters": filters or {},
                "limit": limit,
                "offset": offset,
            },
        )
        try:
            client = self._build_mcp_client()
            payload = self._run_mcp(client.invoke_tool(tool_name, params))
            records = map_from_mcp_response("list", payload)
            return [self._normalize_project_record(record) for record in records]
        except (MCPClientError, ValueError) as exc:
            logger.warning(
                "MCP %s failed for Clarity connector; falling back to REST. Error: %s",
                tool_key,
                exc,
            )
            return rest_call()

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
        return self._list_projects_via_mcp(
            filters=filters,
            limit=limit,
            offset=offset,
            rest_call=lambda: self._read_projects(limit=limit, offset=offset),
        )

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
                projects.append(self._normalize_project_record(item))
        return projects

    def get_schema(self) -> dict[str, Any]:
        return self.SCHEMA


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
