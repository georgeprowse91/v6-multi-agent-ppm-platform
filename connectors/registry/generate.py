#!/usr/bin/env python3
"""Generate connectors/registry/connectors.json from manifest.yaml files.

This script reads every connector's manifest.yaml (the single source of truth)
and produces the JSON catalog used by the web frontend and API routes.

Usage:
    python connectors/registry/generate.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONNECTORS_ROOT = REPO_ROOT / "connectors"
OUTPUT_PATH = REPO_ROOT / "connectors" / "registry" / "connectors.json"

# Map manifest categories to the canonical short names used in connectors.json
_CATEGORY_NORMALIZE: dict[str, str] = {
    "ppm": "ppm",
    "project-portfolio-management": "ppm",
    "work-management": "pm",
    "pm": "pm",
    "devops": "pm",
    "doc_mgmt": "doc_mgmt",
    "document-management": "doc_mgmt",
    "erp": "erp",
    "hris": "hris",
    "collaboration": "collaboration",
    "grc": "grc",
    "it-service": "grc",
    "compliance": "compliance",
    "iot": "iot",
    "crm": "crm",
}

_STATUS_NORMALIZE: dict[str, str] = {
    "available": "production",
    "production": "production",
    "beta": "beta",
    "coming_soon": "coming_soon",
    "coming-soon": "coming_soon",
}

_DIRECTION_NORMALIZE: dict[str, str] = {
    "inbound": "inbound",
    "outbound": "outbound",
    "bidirectional": "bidirectional",
    "bi-directional": "bidirectional",
}


def _manifest_to_entry(data: dict) -> dict | None:
    connector_id = data.get("id")
    if not connector_id:
        return None

    category = _CATEGORY_NORMALIZE.get(str(data.get("category", "")).lower(), "")
    status = _STATUS_NORMALIZE.get(str(data.get("status", "beta")).lower(), "beta")

    sync = data.get("sync") or {}
    raw_dirs = sync.get("directions", [])
    directions = [_DIRECTION_NORMALIZE[d] for d in raw_dirs if d in _DIRECTION_NORMALIZE]
    if not directions:
        directions = ["inbound"]

    maturity = data.get("maturity") or {}
    certification = "certified" if maturity.get("level", 0) >= 2 else (
        "automated" if maturity.get("level", 0) >= 1 else "not-started"
    )

    return {
        "id": connector_id,
        "name": data.get("name", connector_id),
        "manifest_path": f"connectors/{connector_id}/manifest.yaml",
        "status": status,
        "certification": certification,
        "category": category,
        "supported_sync_directions": directions,
    }


def main() -> int:
    entries: list[dict] = []

    for manifest_path in sorted(CONNECTORS_ROOT.glob("*/manifest.yaml")):
        if manifest_path.parent.parent.name == "mock":
            continue
        try:
            data = yaml.safe_load(manifest_path.read_text()) or {}
        except (OSError, yaml.YAMLError) as exc:
            print(f"WARNING: skipping {manifest_path}: {exc}", file=sys.stderr)
            continue

        entry = _manifest_to_entry(data)
        if entry is not None:
            entries.append(entry)

    entries.sort(key=lambda e: e["id"])

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
        f.write("\n")

    print(f"Generated {OUTPUT_PATH} with {len(entries)} connectors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
