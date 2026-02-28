#!/usr/bin/env python3
"""Validate connector manifest.yaml files have required fields and valid YAML."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONNECTORS_DIR = REPO_ROOT / "connectors"

REQUIRED_MANIFEST_FIELDS = {"id", "name", "version", "category"}


def main() -> int:
    if not CONNECTORS_DIR.exists():
        print(f"Connectors directory not found: {CONNECTORS_DIR.relative_to(REPO_ROOT)}")
        return 1

    failures: list[str] = []
    checked = 0
    for manifest in sorted(CONNECTORS_DIR.rglob("manifest.yaml")):
        checked += 1
        relative = manifest.relative_to(REPO_ROOT)
        try:
            with manifest.open(encoding="utf-8") as fh:
                doc = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            failures.append(f"{relative}: invalid YAML: {exc}")
            continue

        if not isinstance(doc, dict):
            failures.append(f"{relative}: root element is not a mapping")
            continue

        missing = REQUIRED_MANIFEST_FIELDS - doc.keys()
        if missing:
            failures.append(f"{relative}: missing required fields: {', '.join(sorted(missing))}")

    if failures:
        print("Manifest validation failures:")
        for f in failures:
            print(f"  {f}")
        return 1

    print(f"Manifest validation passed ({checked} manifests checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
