from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SDK_PATH = REPO_ROOT / "integrations" / "connectors" / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from integrations.connectors.sdk.src.connector_registry import get_connector_definition
from integrations.connectors.sdk.src.project_connector_store import (
    ProjectConnectorConfig,
    ProjectConnectorConfigStore,
)


def test_mcp_project_config_roundtrip(tmp_path: Path) -> None:
    definition = get_connector_definition("slack_mcp")
    assert definition is not None

    store = ProjectConnectorConfigStore(storage_path=tmp_path / "project_config.json")
    config = ProjectConnectorConfig(
        connector_id=definition.connector_id,
        name=definition.name,
        category=definition.category,
        enabled=True,
        ppm_project_id="ppm-456",
        mcp_server_url="https://mcp.example.com",
        mcp_server_id="slack",
        mcp_tool_map={"send_message": "slack.postMessage"},
        prefer_mcp=True,
        mcp_enabled=True,
    )

    store.save(config)
    loaded = store.get("ppm-456", definition.connector_id)

    assert loaded is not None
    assert loaded.mcp_server_url == "https://mcp.example.com"
    assert loaded.mcp_tool_map == {"send_message": "slack.postMessage"}
    assert "send_message" in loaded.mcp_tools
    assert loaded.prefer_mcp is True
    assert loaded.mcp_enabled is True


def test_project_enable_connector_overrides_system(tmp_path: Path) -> None:
    store = ProjectConnectorConfigStore(storage_path=tmp_path / "project_config.json")

    planview = get_connector_definition("planview")
    planview_mcp = get_connector_definition("planview_mcp")
    assert planview is not None
    assert planview_mcp is not None

    planview_config = ProjectConnectorConfig(
        connector_id=planview.connector_id,
        name=planview.name,
        category=planview.category,
        enabled=True,
        ppm_project_id="ppm-789",
    )
    planview_mcp_config = ProjectConnectorConfig(
        connector_id=planview_mcp.connector_id,
        name=planview_mcp.name,
        category=planview_mcp.category,
        enabled=False,
        ppm_project_id="ppm-789",
    )

    store.save(planview_config)
    store.save(planview_mcp_config)

    assert store.enable_connector("ppm-789", "planview_mcp") is True

    updated_planview = store.get("ppm-789", "planview")
    updated_planview_mcp = store.get("ppm-789", "planview_mcp")

    assert updated_planview is not None
    assert updated_planview.enabled is False
    assert updated_planview_mcp is not None
    assert updated_planview_mcp.enabled is True
