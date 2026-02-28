"""
Azure DevOps Connector Implementation.

Supports:
- PAT-based authentication
- Connection testing
- Reading projects and work items
- Writing work items
"""

from __future__ import annotations

import base64
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

from base_connector import ConnectorCategory, ConnectorConfig  # noqa: E402
from http_client import HttpClient, RetryConfig  # noqa: E402
from rest_connector import RestConnector  # noqa: E402
from connector_secrets import resolve_secret  # noqa: E402


class AzureDevOpsConnector(RestConnector):
    CONNECTOR_ID = "azure_devops"
    CONNECTOR_NAME = "Azure DevOps"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.PM
    SUPPORTS_WRITE = True
    IDEMPOTENCY_FIELDS = ("id", "workItemId", "rev")
    CONFLICT_TIMESTAMP_FIELD = "changedDate"

    AUTH_TEST_ENDPOINT = "/_apis/projects"
    AUTH_TEST_PARAMS = {"api-version": "7.0", "$top": 1}
    RESOURCE_PATHS = {
        "projects": {"path": "/_apis/projects", "items_path": "value"},
        "work_items": {
            "path": "/_apis/wit/workitems",
            "items_path": "value",
            "write_path": "/_apis/wit/workitems",
            "write_method": "POST",
        },
    }
    SCHEMA = {
        "projects": {"id": "string", "name": "string", "state": "string"},
        "work_items": {"id": "integer", "title": "string", "state": "string"},
    }
    RATE_LIMIT_PER_MINUTE = 60

    def __init__(
        self,
        config: ConnectorConfig,
        *,
        client: HttpClient | None = None,
        transport: Any | None = None,
    ) -> None:
        super().__init__(config, client=client, transport=transport)

    def _get_credentials(self) -> tuple[str, str]:
        organization_url = resolve_secret(os.getenv("AZURE_DEVOPS_ORG_URL")) or self.config.instance_url
        pat = resolve_secret(os.getenv("AZURE_DEVOPS_PAT"))
        if not organization_url:
            raise ValueError("AZURE_DEVOPS_ORG_URL environment variable is required")
        if not pat:
            raise ValueError("AZURE_DEVOPS_PAT environment variable is required")
        return organization_url, pat

    def _build_client(self) -> HttpClient:
        if self._client:
            return self._client
        organization_url, pat = self._get_credentials()
        token = f":{pat}".encode("utf-8")
        auth_header = base64.b64encode(token).decode("utf-8")
        retry_config = RetryConfig(
            max_retries=3,
            backoff_factor=0.5,
            retry_statuses=(429, 500, 502, 503, 504),
        )
        self._client = HttpClient(
            base_url=organization_url,
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
