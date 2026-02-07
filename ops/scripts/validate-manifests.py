#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "connectors" / "registry" / "schemas" / "connector-manifest.schema.json"
CONNECTORS_DIR = REPO_ROOT / "connectors"


def main() -> int:
    schema = json.loads(SCHEMA_PATH.read_text())
    validator = Draft202012Validator(schema)
    failures: list[str] = []

    for manifest_path in sorted(CONNECTORS_DIR.glob("*/manifest.yaml")):
        data = yaml.safe_load(manifest_path.read_text())
        errors = sorted(validator.iter_errors(data), key=lambda err: err.path)
        if errors:
            formatted = "; ".join(error.message for error in errors)
            failures.append(f"{manifest_path}: {formatted}")

    if failures:
        for failure in failures:
            print(f"Manifest validation failed: {failure}")
        return 1

    print("Manifest validation succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
