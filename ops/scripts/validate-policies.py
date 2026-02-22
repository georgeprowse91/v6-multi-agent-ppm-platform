#!/usr/bin/env python3
"""Validate policy bundles against their JSON schema and semantic checks."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import yaml
from jsonschema import Draft202012Validator

DEFAULT_BUNDLE_PATHS = [
    Path("apps/orchestration-service/policies/bundles/default-policy-bundle.yaml"),
    Path("apps/document-service/policies/bundles/default-policy-bundle.yaml"),
    Path("services/policy-engine/policies/bundles/default-policy-bundle.yaml"),
    Path("ops/infra/policies/dlp/bundles/default-dlp-policy-bundle.yaml"),
    Path("ops/infra/policies/network/bundles/default-network-policy-bundle.yaml"),
    Path("ops/infra/policies/security/bundles/default-security-policy-bundle.yaml"),
]


class PolicyValidationError(Exception):
    pass


def _find_schema(start: Path) -> Path:
    for parent in [start, *start.parents]:
        candidate = parent / "schema" / "policy-bundle.schema.json"
        if candidate.exists():
            return candidate
    raise PolicyValidationError(f"No schema found for {start}")


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise PolicyValidationError(f"Policy bundle {path} must be a YAML mapping")
    return data


def _validate_semantics(bundle: dict, bundle_path: Path) -> None:
    policies = bundle.get("policies", [])
    ids = [policy.get("id") for policy in policies]
    if len(ids) != len(set(ids)):
        raise PolicyValidationError(f"Duplicate policy IDs in {bundle_path}")
    metadata = bundle.get("metadata", {})
    if not metadata.get("name"):
        raise PolicyValidationError(f"metadata.name is required in {bundle_path}")


def validate_policy_bundle(bundle_path: Path) -> None:
    schema_path = _find_schema(bundle_path)
    schema = json.loads(schema_path.read_text())
    bundle = _load_yaml(bundle_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(bundle), key=lambda e: e.path)
    if errors:
        formatted = "\n".join(f"- {error.message}" for error in errors)
        raise PolicyValidationError(f"Schema validation failed for {bundle_path}:\n{formatted}")
    _validate_semantics(bundle, bundle_path)


def validate_policy_bundles(paths: Iterable[Path]) -> None:
    for path in paths:
        if not path.exists():
            raise PolicyValidationError(f"Missing policy bundle: {path}")
        validate_policy_bundle(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate policy bundles.")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Optional policy bundle paths. Defaults to repo bundles.",
    )
    args = parser.parse_args()
    paths_list = list(args.paths or DEFAULT_BUNDLE_PATHS)
    validate_policy_bundles(paths_list)
    print(f"Validated {len(paths_list)} policy bundle(s) successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
