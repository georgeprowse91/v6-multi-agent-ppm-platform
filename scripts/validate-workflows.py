#!/usr/bin/env python3
"""Validate workflow definitions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import yaml
from jsonschema import Draft202012Validator

DEFAULT_WORKFLOWS = [
    Path("apps/workflow-engine/workflows/definitions/intake-triage.workflow.yaml"),
    Path("examples/workflows/portfolio-intake.workflow.yaml"),
]

SCHEMA_PATH = Path("apps/workflow-engine/workflows/schema/workflow.schema.json")


class WorkflowValidationError(Exception):
    pass


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise WorkflowValidationError(f"Workflow {path} must be a YAML mapping")
    return data


def validate_workflow_definition(path: Path) -> None:
    if not SCHEMA_PATH.exists():
        raise WorkflowValidationError(f"Missing schema: {SCHEMA_PATH}")
    schema = json.loads(SCHEMA_PATH.read_text())
    definition = _load_yaml(path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(definition), key=lambda e: e.path)
    if errors:
        formatted = "\n".join(f"- {error.message}" for error in errors)
        raise WorkflowValidationError(f"Schema validation failed for {path}:\n{formatted}")


def validate_workflows(paths: Iterable[Path]) -> None:
    for path in paths:
        if not path.exists():
            raise WorkflowValidationError(f"Missing workflow definition: {path}")
        validate_workflow_definition(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate workflow definitions.")
    parser.add_argument("paths", nargs="*", type=Path, help="Optional workflow paths")
    args = parser.parse_args()
    workflows = list(args.paths or DEFAULT_WORKFLOWS)
    validate_workflows(workflows)
    print(f"Validated {len(workflows)} workflow definition(s) successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
