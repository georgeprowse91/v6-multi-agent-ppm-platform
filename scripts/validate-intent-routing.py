#!/usr/bin/env python3
"""Validate intent routing configuration."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

DEFAULT_CONFIG = Path("config/agents/intent-routing.yaml")
SCHEMA_PATH = Path("config/agents/schema/intent-routing.schema.json")


class IntentRoutingValidationError(Exception):
    pass


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise IntentRoutingValidationError(f"Intent routing config must be a YAML mapping: {path}")
    return data


def validate_config(path: Path) -> None:
    if not SCHEMA_PATH.exists():
        raise IntentRoutingValidationError(f"Missing schema: {SCHEMA_PATH}")
    schema = json.loads(SCHEMA_PATH.read_text())
    payload = _load_yaml(path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    if errors:
        formatted = "\n".join(f"- {error.message}" for error in errors)
        raise IntentRoutingValidationError(f"Schema validation failed for {path}:\n{formatted}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate intent routing config.")
    parser.add_argument("paths", nargs="*", type=Path, help="Optional config path(s)")
    args = parser.parse_args()
    targets = list(args.paths or [DEFAULT_CONFIG])
    for path in targets:
        if not path.exists():
            raise IntentRoutingValidationError(f"Missing config: {path}")
        validate_config(path)
    print(f"Validated {len(targets)} intent routing config file(s) successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
