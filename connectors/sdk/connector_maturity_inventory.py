#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
CONNECTORS_ROOT = REPO_ROOT / "integrations" / "connectors"


def _read_manifest(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text())


def _mapping_completeness(connector_dir: Path, manifest: dict[str, Any]) -> float:
    mappings = manifest.get("mappings", [])
    if not mappings:
        return 0.0
    present = 0
    for mapping in mappings:
        mapping_file = mapping.get("mapping_file")
        if mapping_file and (connector_dir / mapping_file).exists():
            present += 1
    return round(present / len(mappings), 2)


def build_inventory() -> dict[str, Any]:
    connectors: list[dict[str, Any]] = []
    for manifest_path in sorted(CONNECTORS_ROOT.glob("*/manifest.yaml")):
        connector_dir = manifest_path.parent
        manifest = _read_manifest(manifest_path)
        maturity = manifest.get("maturity", {})
        capabilities = maturity.get("capabilities", {})
        coverage = {
            "read": bool(capabilities.get("read")),
            "write": bool(capabilities.get("write")),
            "webhook": bool(capabilities.get("webhook") or manifest.get("sync", {}).get("supports_webhooks")),
            "mapping_completeness": _mapping_completeness(connector_dir, manifest),
        }
        connectors.append(
            {
                "id": manifest["id"],
                "name": manifest.get("name"),
                "level": maturity.get("level", 0),
                "business_priority": maturity.get("business_priority", 999),
                "coverage": coverage,
            }
        )

    gaps = {
        "missing_write": sorted([c["id"] for c in connectors if not c["coverage"]["write"]]),
        "missing_webhook": sorted([c["id"] for c in connectors if not c["coverage"]["webhook"]]),
        "incomplete_mapping": sorted(
            [c["id"] for c in connectors if c["coverage"]["mapping_completeness"] < 1.0]
        ),
    }

    return {
        "summary": {
            "total_connectors": len(connectors),
            "read_enabled": sum(1 for c in connectors if c["coverage"]["read"]),
            "write_enabled": sum(1 for c in connectors if c["coverage"]["write"]),
            "webhook_enabled": sum(1 for c in connectors if c["coverage"]["webhook"]),
        },
        "connectors": sorted(connectors, key=lambda c: (c["business_priority"], c["id"])),
        "gaps": gaps,
    }


if __name__ == "__main__":
    print(json.dumps(build_inventory(), indent=2))
