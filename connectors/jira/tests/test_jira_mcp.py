"""MCP behavior tests for the Jira connector."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
CONNECTOR_SDK_PATH = REPO_ROOT / "connectors" / "sdk" / "src"
JIRA_CONNECTOR_PATH = REPO_ROOT / "connectors" / "jira" / "src"
for path in (REPO_ROOT, CONNECTOR_SDK_PATH, JIRA_CONNECTOR_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from base_connector import ConnectorCategory, ConnectorConfig, SyncDirection, SyncFrequency
from jira_connector import JiraConnector
from mcp_client.errors import MCPServerError, MCPToolNotFoundError


class FakeMCPClient:
    def __init__(self, payload: Any, error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def list_records(self, params: dict[str, Any]) -> Any:
        self.calls.append(params)
        if self.error:
            raise self.error
        return self.payload


@pytest.fixture
def jira_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_id="jira",
        name="Jira",
        category=ConnectorCategory.PM,
        enabled=True,
        sync_direction=SyncDirection.INBOUND,
        sync_frequency=SyncFrequency.DAILY,
        instance_url="https://jira.example.com",
        prefer_mcp=True,
        mcp_server_url="https://mcp.example.com",
    )


def test_jira_mcp_invocation_and_mapping(jira_config: ConnectorConfig) -> None:
    payload = {
        "values": [
            {
                "id": "100",
                "key": "APP",
                "name": "App Project",
                "projectTypeKey": "software",
            }
        ]
    }
    fake_client = FakeMCPClient(payload)
    connector = JiraConnector(jira_config, mcp_client=fake_client)
    connector._authenticated = True
    connector._client = object()

    with patch.object(connector, "_read_projects", return_value=[]):
        result = connector.read("projects", limit=50, offset=5)

    assert fake_client.calls == [
        {"resource_type": "projects", "filters": {}, "limit": 50, "offset": 5}
    ]
    assert result == [
        {
            "id": "100",
            "key": "APP",
            "name": "App Project",
            "description": None,
            "lead": None,
            "project_type": "software",
        }
    ]


@pytest.mark.parametrize(
    "error",
    [MCPToolNotFoundError("missing"), MCPServerError("rpc failed")],
)
def test_jira_mcp_fallbacks(jira_config: ConnectorConfig, error: Exception) -> None:
    fake_client = FakeMCPClient(payload={}, error=error)
    connector = JiraConnector(jira_config, mcp_client=fake_client)
    connector._authenticated = True
    connector._client = object()
    rest_records = [{"id": "rest-project", "key": "REST", "name": "REST"}]

    with patch.object(connector, "_read_projects", return_value=rest_records):
        result = connector.read("projects")

    assert result == rest_records
