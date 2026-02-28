from __future__ import annotations

from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SDK_PATH = REPO_ROOT / "connectors" / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from connectors.sdk.src.connector_registry import get_all_connectors
from connectors.sdk.src.project_connector_store import (
    ProjectConnectorConfig,
    ProjectConnectorConfigStore,
)


def _rest_connectors():
    return [connector for connector in get_all_connectors() if connector.auth_type != "mcp"]


@pytest.mark.parametrize("definition", _rest_connectors())
def test_project_level_config_roundtrip(definition, tmp_path: Path) -> None:
    store = ProjectConnectorConfigStore(storage_path=tmp_path / "project_config.json")
    config = ProjectConnectorConfig(
        connector_id=definition.connector_id,
        name=definition.name,
        category=definition.category,
        enabled=False,
        ppm_project_id="ppm-123",
    )

    store.save(config)
    loaded = store.get("ppm-123", definition.connector_id)

    assert loaded is not None
    assert loaded.ppm_project_id == "ppm-123"
    assert loaded.connector_id == definition.connector_id
    assert loaded.name == definition.name
    assert loaded.category == definition.category


def test_rest_connector_docs_cover_all() -> None:
    doc_path = REPO_ROOT / "docs" / "connectors" / "rest-connector-config.md"
    content = doc_path.read_text()
    for definition in _rest_connectors():
        assert f"| {definition.connector_id} " in content
