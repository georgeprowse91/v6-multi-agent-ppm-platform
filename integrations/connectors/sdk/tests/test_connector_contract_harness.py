from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "integrations" / "connectors" / "sdk" / "src"))
from runtime import ConnectorRuntime

CONNECTORS_ROOT = REPO_ROOT / "integrations" / "connectors"
REGISTRY_PATH = CONNECTORS_ROOT / "registry" / "connectors.json"


def _connector_dirs() -> list[Path]:
    registry_entries = json.loads(REGISTRY_PATH.read_text())
    return sorted(CONNECTORS_ROOT / item["id"] for item in registry_entries)


def _manifest_paths() -> list[Path]:
    return [connector_dir / "manifest.yaml" for connector_dir in _connector_dirs()]


def test_all_registry_connectors_have_required_layout() -> None:
    for connector_dir in _connector_dirs():
        assert connector_dir.exists(), f"missing connector directory {connector_dir.name}"
        assert (connector_dir / "manifest.yaml").exists(), f"missing manifest.yaml for {connector_dir.name}"
        assert (connector_dir / "src" / "main.py").exists(), f"missing src/main.py for {connector_dir.name}"
        assert (connector_dir / "mappings").is_dir(), f"missing mappings/ for {connector_dir.name}"
        assert (connector_dir / "tests").is_dir(), f"missing tests/ for {connector_dir.name}"


def test_all_connector_manifests_include_maturity() -> None:
    for manifest_path in _manifest_paths():
        data = yaml.safe_load(manifest_path.read_text())
        maturity = data.get("maturity")
        assert isinstance(maturity, dict), f"missing maturity for {manifest_path.parent.name}"
        assert 0 <= maturity.get("level", -1) <= 3


def test_manifest_declares_required_capabilities() -> None:
    for manifest_path in _manifest_paths():
        data = yaml.safe_load(manifest_path.read_text())
        caps = data["maturity"]["capabilities"]
        for required in (
            "read",
            "write",
            "webhook",
            "declarative_mapping",
            "idempotent_write",
            "conflict_handling",
        ):
            assert required in caps, f"{data['id']} missing {required} capability flag"


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


def test_every_connector_has_at_least_one_test_file() -> None:
    for connector_dir in _connector_dirs():
        test_files = list((connector_dir / "tests").glob("test_*.py"))
        assert test_files, f"{connector_dir.name} must define at least one test file"
