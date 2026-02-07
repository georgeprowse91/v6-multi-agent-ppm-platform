#!/usr/bin/env python3
"""Validate connector hub sandbox configurations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import yaml
from jsonschema import Draft202012Validator

DEFAULT_CONFIGS = [
    Path("integrations/apps/connector-hub/sandbox/examples/github-sandbox-connector.yaml"),
]

SCHEMA_PATH = Path("integrations/apps/connector-hub/sandbox/schema/sandbox-connector.schema.json")


class SandboxValidationError(Exception):
    pass


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise SandboxValidationError(f"Sandbox config {path} must be a YAML mapping")
    return data


def validate_sandbox_config(path: Path) -> None:
    if not SCHEMA_PATH.exists():
        raise SandboxValidationError(f"Missing schema: {SCHEMA_PATH}")
    schema = json.loads(SCHEMA_PATH.read_text())
    config = _load_yaml(path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(config), key=lambda e: e.path)
    if errors:
        formatted = "\n".join(f"- {error.message}" for error in errors)
        raise SandboxValidationError(f"Schema validation failed for {path}:\n{formatted}")


def validate_sandbox_configs(paths: Iterable[Path]) -> None:
    for path in paths:
        if not path.exists():
            raise SandboxValidationError(f"Missing sandbox config: {path}")
        validate_sandbox_config(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate connector sandbox configs.")
    parser.add_argument("paths", nargs="*", type=Path, help="Optional sandbox config paths")
    args = parser.parse_args()
    configs = list(args.paths or DEFAULT_CONFIGS)
    validate_sandbox_configs(configs)
    print(f"Validated {len(configs)} sandbox config(s) successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
