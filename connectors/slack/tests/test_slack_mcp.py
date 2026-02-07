"""MCP behavior tests for the Slack connector."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CONNECTOR_SDK_PATH = REPO_ROOT / "connectors" / "sdk" / "src"
SLACK_CONNECTOR_PATH = REPO_ROOT / "connectors" / "slack" / "src"
for path in (REPO_ROOT, CONNECTOR_SDK_PATH, SLACK_CONNECTOR_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from base_connector import ConnectorCategory, ConnectorConfig, SyncDirection, SyncFrequency
from mcp_client import MCPClientError
from rest_connector import OAuth2RestConnector
from slack_connector import SlackConnector


class FakeMCPClient:
    def __init__(self, payload: Any, error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def invoke_tool(self, tool_name: str, params: dict[str, Any]) -> Any:
        self.calls.append((tool_name, params))
        if self.error:
            raise self.error
        return self.payload


@pytest.fixture
def slack_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_id="slack",
        name="Slack",
        category=ConnectorCategory.COLLABORATION,
        enabled=True,
        sync_direction=SyncDirection.INBOUND,
        sync_frequency=SyncFrequency.DAILY,
        instance_url="https://slack.example.com",
        prefer_mcp=True,
        mcp_server_url="https://mcp.example.com",
    )


def test_slack_mcp_invocation_and_mapping(slack_config: ConnectorConfig) -> None:
    payload = {"channels": [{"id": "C1", "name": "general"}]}
    fake_client = FakeMCPClient(payload)
    connector = SlackConnector(slack_config)

    with patch.object(connector, "_build_mcp_client", return_value=fake_client), patch.object(
        OAuth2RestConnector, "read", return_value=[]
    ):
        result = connector.read("channels", limit=25, offset=1)

    assert fake_client.calls == [
        (
            "slack.listChannels",
            {"resource_type": "channels", "filters": {}, "limit": 25, "offset": 1},
        )
    ]
    assert result == [{"id": "C1", "name": "general"}]


def test_slack_mcp_tool_missing_falls_back(slack_config: ConnectorConfig) -> None:
    connector = SlackConnector(slack_config)
    connector._mcp_tool_map = {}
    rest_records = [{"id": "rest-channel"}]

    with patch.object(OAuth2RestConnector, "read", return_value=rest_records):
        result = connector.read("channels")

    assert result == rest_records


def test_slack_mcp_error_falls_back(slack_config: ConnectorConfig) -> None:
    connector = SlackConnector(slack_config)
    rest_records = [{"id": "rest-channel"}]
    fake_client = FakeMCPClient(payload={}, error=MCPClientError("boom"))

    with patch.object(connector, "_build_mcp_client", return_value=fake_client), patch.object(
        OAuth2RestConnector, "read", return_value=rest_records
    ):
        result = connector.read("channels")

    assert result == rest_records
