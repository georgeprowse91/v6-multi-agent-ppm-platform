#!/usr/bin/env python3
"""Validate canonical template YAML manifests in docs/templates/canonical/."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = REPO_ROOT / "docs" / "templates" / "canonical"

REQUIRED_FIELDS = {"id", "name", "version"}


def main() -> int:
    if not TEMPLATES_DIR.exists():
        print(f"Templates directory not found: {TEMPLATES_DIR.relative_to(REPO_ROOT)}")
        return 0

    failures: list[str] = []
    checked = 0
    for path in sorted(TEMPLATES_DIR.rglob("*.yaml")):
        checked += 1
        try:
            with path.open(encoding="utf-8") as fh:
                doc = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            failures.append(f"{path.relative_to(REPO_ROOT)}: invalid YAML: {exc}")
            continue

        if not isinstance(doc, dict):
            failures.append(f"{path.relative_to(REPO_ROOT)}: root element is not a mapping")
            continue

        missing = REQUIRED_FIELDS - doc.keys()
        if missing:
            failures.append(
                f"{path.relative_to(REPO_ROOT)}: missing required fields: {', '.join(sorted(missing))}"
            )

    if failures:
        print("Template validation failures:")
        for f in failures:
            print(f"  {f}")
        return 1

    print(f"Template validation passed ({checked} templates checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
