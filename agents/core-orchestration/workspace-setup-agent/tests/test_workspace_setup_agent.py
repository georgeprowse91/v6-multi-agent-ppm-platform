from __future__ import annotations

import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[4]
SRC_DIR = TESTS_DIR.parent / "src"
sys.path.extend(
    [
        str(SRC_DIR),
        str(REPO_ROOT),
        str(REPO_ROOT / "packages"),
        str(REPO_ROOT / "agents" / "runtime"),
        str(REPO_ROOT / "integrations" / "services" / "integration"),
    ]
)

from workspace_setup_agent import WorkspaceSetupAgent


class DummyEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.published.append((topic, payload))

    async def subscribe(self, *args, **kwargs) -> None:
        return None


def _make_agent(event_bus: DummyEventBus | None = None) -> WorkspaceSetupAgent:
    return WorkspaceSetupAgent(
        config={
            "event_bus": event_bus or DummyEventBus(),
        }
    )


@pytest.mark.anyio
async def test_initialise_workspace_creates_workspace() -> None:
    bus = DummyEventBus()
    agent = _make_agent(bus)
    result = await agent.execute(
        {
            "action": "initialise_workspace",
            "project_id": "proj-001",
            "tenant_id": "tenant-1",
        }
    )
    assert result["success"] is True
    assert result.get("workspace_id")
    workspace = result["workspace"]
    assert workspace["project_id"] == "proj-001"
    assert workspace["tenant_id"] == "tenant-1"
    assert workspace["status"] == "initialising"
    assert "methodology_map" in workspace["canvas_tabs"]


@pytest.mark.anyio
async def test_initialise_workspace_requires_project_id() -> None:
    agent = _make_agent()
    result = await agent.execute(
        {
            "action": "initialise_workspace",
            "tenant_id": "tenant-1",
        }
    )
    assert result["success"] is False
    assert "project_id" in result.get("error", "")


@pytest.mark.anyio
async def test_validate_connectors_requires_workspace_id() -> None:
    agent = _make_agent()
    result = await agent.execute(
        {
            "action": "validate_connectors",
            "tenant_id": "tenant-1",
            "connectors": [
                {"connector_id": "jira-1", "category": "pm_tools", "status": "connected"}
            ],
        }
    )
    assert result["success"] is False
    assert "workspace_id" in result.get("error", "")


@pytest.mark.anyio
async def test_validate_connectors_after_init() -> None:
    agent = _make_agent()
    init_result = await agent.execute(
        {
            "action": "initialise_workspace",
            "project_id": "proj-002",
            "tenant_id": "tenant-2",
        }
    )
    workspace_id = init_result["workspace_id"]

    result = await agent.execute(
        {
            "action": "validate_connectors",
            "tenant_id": "tenant-2",
            "workspace_id": workspace_id,
            "connectors": [
                {
                    "connector_id": "jira-main",
                    "category": "pm_tools",
                    "status": "permissions_validated",
                }
            ],
        }
    )
    assert result["success"] is True
    assert result.get("results")


@pytest.mark.anyio
async def test_test_connection_returns_connected() -> None:
    agent = _make_agent()
    result = await agent.execute(
        {
            "action": "test_connection",
            "tenant_id": "tenant-1",
            "connector_id": "jira-main",
        }
    )
    assert result["success"] is True
    assert result["connection_status"] == "connected"
    assert result["connector_id"] == "jira-main"


@pytest.mark.anyio
async def test_select_methodology_valid() -> None:
    agent = _make_agent()
    init_result = await agent.execute(
        {
            "action": "initialise_workspace",
            "project_id": "proj-003",
            "tenant_id": "tenant-3",
        }
    )
    workspace_id = init_result["workspace_id"]

    result = await agent.execute(
        {
            "action": "select_methodology",
            "tenant_id": "tenant-3",
            "workspace_id": workspace_id,
            "methodology": "adaptive",
        }
    )
    assert result["success"] is True
    assert result.get("methodology") == "adaptive"


@pytest.mark.anyio
async def test_unknown_action_returns_error() -> None:
    agent = _make_agent()
    result = await agent.execute(
        {
            "action": "do_something_unknown",
            "tenant_id": "tenant-1",
        }
    )
    assert result["success"] is False
    assert "Unknown action" in result.get("error", "")
    assert "supported_actions" in result


@pytest.mark.anyio
async def test_get_setup_status_after_init() -> None:
    agent = _make_agent()
    init_result = await agent.execute(
        {
            "action": "initialise_workspace",
            "project_id": "proj-004",
            "tenant_id": "tenant-4",
        }
    )
    workspace_id = init_result["workspace_id"]

    result = await agent.execute(
        {
            "action": "get_setup_status",
            "tenant_id": "tenant-4",
            "workspace_id": workspace_id,
        }
    )
    assert result["success"] is True
    assert result.get("workspace_id") == workspace_id
