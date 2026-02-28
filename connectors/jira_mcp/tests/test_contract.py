from __future__ import annotations

from pathlib import Path

from connectors.sdk.src.runtime import ConnectorRuntime

CONNECTOR_ROOT = Path(__file__).resolve().parents[1]


def test_manifest_and_mappings_validate() -> None:
    runtime = ConnectorRuntime(CONNECTOR_ROOT)
    for mapping in runtime.manifest.mappings:
        runtime._load_mapping(CONNECTOR_ROOT / mapping["mapping_file"])
