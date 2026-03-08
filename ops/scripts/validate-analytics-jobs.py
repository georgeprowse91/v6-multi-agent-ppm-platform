#!/usr/bin/env python3
"""Validate analytics job manifests."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import yaml
from jsonschema import Draft202012Validator

DEFAULT_MANIFESTS = [
    Path("services/analytics-service/jobs/manifests/daily-portfolio-rollup.yaml"),
]

SCHEMA_PATH = Path("services/analytics-service/jobs/schema/job-manifest.schema.json")


class JobValidationError(Exception):
    pass


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise JobValidationError(f"Job manifest {path} must be a YAML mapping")
    return data


def validate_job_manifest(manifest_path: Path) -> None:
    if not SCHEMA_PATH.exists():
        raise JobValidationError(f"Missing schema: {SCHEMA_PATH}")
    schema = json.loads(SCHEMA_PATH.read_text())
    manifest = _load_yaml(manifest_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(manifest), key=lambda e: e.path)
    if errors:
        formatted = "\n".join(f"- {error.message}" for error in errors)
        raise JobValidationError(f"Schema validation failed for {manifest_path}:\n{formatted}")


def validate_job_manifests(paths: Iterable[Path]) -> None:
    for path in paths:
        if not path.exists():
            raise JobValidationError(f"Missing job manifest: {path}")
        validate_job_manifest(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate analytics job manifests.")
    parser.add_argument("paths", nargs="*", type=Path, help="Optional manifest paths")
    args = parser.parse_args()
    manifests = list(args.paths or DEFAULT_MANIFESTS)
    validate_job_manifests(manifests)
    print(f"Validated {len(manifests)} analytics job manifest(s) successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
