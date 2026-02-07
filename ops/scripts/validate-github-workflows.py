#!/usr/bin/env python3
"""Validate GitHub Actions workflow YAML structure."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import yaml

WORKFLOW_DIR = Path(".github/workflows")
DEFAULT_WORKFLOWS = sorted(
    [path for path in WORKFLOW_DIR.glob("*.yml") if path.name != "README.md"]
)


class WorkflowFileError(Exception):
    pass


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise WorkflowFileError(f"Workflow {path} must be a YAML mapping")
    return data


def validate_workflow_file(path: Path) -> None:
    data = _load_yaml(path)
    required_keys = {"name", "jobs"}
    missing = required_keys - set(data.keys())
    if missing:
        raise WorkflowFileError(f"{path} is missing required key(s) {sorted(missing)}")
    if "on" not in data and True not in data:
        raise WorkflowFileError(f"{path} is missing required key 'on'")


def validate_workflow_files(paths: Iterable[Path]) -> None:
    for path in paths:
        if not path.exists():
            raise WorkflowFileError(f"Missing workflow file: {path}")
        validate_workflow_file(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate GitHub workflow YAML files.")
    parser.add_argument("paths", nargs="*", type=Path, help="Optional workflow file paths")
    args = parser.parse_args()
    workflow_files = list(args.paths or DEFAULT_WORKFLOWS)
    validate_workflow_files(workflow_files)
    print(f"Validated {len(workflow_files)} GitHub workflow file(s) successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
