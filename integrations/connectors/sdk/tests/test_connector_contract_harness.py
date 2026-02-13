from __future__ import annotations

from pathlib import Path
import sys

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "integrations" / "connectors" / "sdk" / "src"))
from runtime import ConnectorRuntime

CONNECTORS_ROOT = REPO_ROOT / "integrations" / "connectors"


def _manifest_paths() -> list[Path]:
    return sorted(CONNECTORS_ROOT.glob("*/manifest.yaml"))


def test_all_connector_manifests_include_maturity() -> None:
    for manifest_path in _manifest_paths():
        data = yaml.safe_load(manifest_path.read_text())
        maturity = data.get("maturity")
        assert isinstance(maturity, dict), f"missing maturity for {manifest_path.parent.name}"
        assert 0 <= maturity.get("level", -1) <= 3


def test_level2_connectors_conformance_requirements() -> None:
    for manifest_path in _manifest_paths():
        data = yaml.safe_load(manifest_path.read_text())
        maturity = data["maturity"]
        if maturity.get("level", 0) < 2:
            continue
        caps = maturity.get("capabilities", {})
        assert caps.get("read") is True, f"{data['id']} must support read"
        assert caps.get("write") is True, f"{data['id']} must support write"
        assert caps.get("idempotent_write") is True, f"{data['id']} missing idempotent_write"
        assert caps.get("conflict_handling") is True, f"{data['id']} missing conflict_handling"


def test_mapping_files_validate_via_runtime_loader() -> None:
    for manifest_path in _manifest_paths():
        connector_root = manifest_path.parent
        runtime = ConnectorRuntime(connector_root)
        for mapping in runtime.manifest.mappings:
            runtime._load_mapping(connector_root / mapping["mapping_file"])
