from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize connector metadata and mappings.")
    parser.add_argument("--connector-root", required=True)
    parser.add_argument("--json", action="store_true", help="Output summary as JSON.")
    return parser.parse_args()


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def _summarize_connector(root: Path) -> dict[str, Any]:
    manifest = _load_manifest(root / "manifest.yaml")
    mappings_dir = root / "mappings"
    mapping_files = sorted(p.name for p in mappings_dir.glob("*.yaml")) if mappings_dir.exists() else []
    tests_dir = root / "tests"

    summary = {
        "connector_id": manifest.get("id", root.name),
        "version": manifest.get("version"),
        "root": str(root),
        "mapping_files": mapping_files,
        "has_tests": tests_dir.exists(),
    }
    return summary


def main() -> None:
    args = _parse_args()
    root = Path(args.connector_root).resolve()
    summary = _summarize_connector(root)
    if args.json:
        print(json.dumps(summary, indent=2))
        return

    print(f"Connector: {summary['connector_id']}")
    print(f"Version: {summary['version']}")
    print(f"Root: {summary['root']}")
    print(f"Mapping files: {', '.join(summary['mapping_files']) or 'none'}")
    print(f"Has tests: {summary['has_tests']}")


if __name__ == "__main__":
    main()
