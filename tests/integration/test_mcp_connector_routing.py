from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = Path(__file__).resolve().parents[1]
sys.path = [path for path in sys.path if Path(path).resolve() != TESTS_ROOT]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integrations.connectors.integration.framework import (
    BaseIntegrationConnector,
    ConnectorRegistry,
    IntegrationAuthType,
    IntegrationConfig,
)
from integrations.connectors.integration.mcp_connectors import (
    PlanviewMcpConnector,
    SlackMcpConnector,
)
from integrations.connectors.mcp_client.errors import MCPToolNotFoundError


class DummyMcpClient:
    def __init__(self, responses: dict[str, Any]) -> None:
        self._responses = responses

    async def invoke_tool(self, tool_name: str, params: dict[str, Any]) -> Any:
        if tool_name not in self._responses:
            raise MCPToolNotFoundError(f"Tool {tool_name} not found")
        return self._responses[tool_name]


class DummyRestConnector(BaseIntegrationConnector):
    system_name = "dummy"

    def __init__(self, responses: dict[str, Any], config: IntegrationConfig) -> None:
        super().__init__(config)
        self._responses = responses

    def fetch(self, endpoint: str) -> Any:  # type: ignore[override]
        return self._responses.get(endpoint, [])

    def post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:  # type: ignore[override]
        return self._responses.get(endpoint, {"endpoint": endpoint, "payload": payload})


class RegistryRestConnector(BaseIntegrationConnector):
    system_name = "registry-rest"

    def list_projects(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return []


def test_registry_prefers_mcp_when_enabled() -> None:
    registry = ConnectorRegistry()
    registry.register(SlackMcpConnector.system_name, SlackMcpConnector, variant="mcp")

    config = IntegrationConfig(
        system="slack",
        base_url="https://slack.com/api",
        auth_type=IntegrationAuthType.NONE,
        mcp_server_url="https://mcp.example.com",
        prefer_mcp=True,
    )
    connector = registry.create("slack", config)

    assert isinstance(connector, SlackMcpConnector)


def test_registry_falls_back_to_rest_when_mcp_disabled() -> None:
    registry = ConnectorRegistry()
    registry.register("slack", SlackMcpConnector, variant="mcp")
    registry.register("slack", RegistryRestConnector, variant="rest")

    config = IntegrationConfig(
        system="slack",
        base_url="https://slack.com/api",
        auth_type=IntegrationAuthType.NONE,
        prefer_mcp=False,
    )

    connector = registry.create("slack", config)

    assert isinstance(connector, RegistryRestConnector)


def test_planview_mcp_merges_rest_costs() -> None:
    responses = {
        "planview.listProjects": [{"id": "p-1", "name": "Apollo"}],
    }
    rest_responses = {"/api/v1/projects/costs": [{"id": "p-1", "cost": 1200}]}
    config = IntegrationConfig(
        system="planview",
        base_url="https://planview.example.com",
        auth_type=IntegrationAuthType.NONE,
        mcp_server_url="https://mcp.example.com",
        mcp_tool_map={"list_projects": "planview.listProjects"},
        prefer_mcp=True,
    )

    connector = PlanviewMcpConnector(
        config,
        mcp_client=DummyMcpClient(responses),
        rest_connector=DummyRestConnector(rest_responses, config),
    )
    projects = connector.list_projects(include_costs=True)

    assert projects[0]["id"] == "p-1"
    assert projects[0]["cost"] == 1200


def test_mcp_fallback_to_rest_when_tool_missing() -> None:
    config = IntegrationConfig(
        system="slack",
        base_url="https://slack.com/api",
        auth_type=IntegrationAuthType.NONE,
        mcp_server_url="https://mcp.example.com",
        mcp_tool_map={"send_message": "slack.postMessage"},
        prefer_mcp=True,
    )
    rest_connector = DummyRestConnector({"/chat.postMessage": {"status": "sent"}}, config)
    connector = SlackMcpConnector(
        config,
        mcp_client=DummyMcpClient({}),
        rest_connector=rest_connector,
    )

    response = connector.send_message({"text": "hello"})

    assert response["status"] == "sent"
