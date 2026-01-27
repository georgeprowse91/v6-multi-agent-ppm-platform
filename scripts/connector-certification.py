#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "connectors" / "registry" / "connectors.json"
SCHEMA_PATH = REPO_ROOT / "connectors" / "registry" / "schemas" / "connector-manifest.schema.json"
DATA_SCHEMA_DIR = REPO_ROOT / "data" / "schemas"

CERTIFIABLE_STATUSES = {"beta", "production"}


@dataclass
class CertificationResult:
    connector_id: str
    status: str
    certification: str
    errors: list[str]


def _load_registry() -> list[dict[str, Any]]:
    return json.loads(REGISTRY_PATH.read_text())


def _load_manifest(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text())


def _validate_manifest_schema(validator: Draft202012Validator, manifest: dict[str, Any]) -> list[str]:
    errors = sorted(validator.iter_errors(manifest), key=lambda err: err.path)
    return [error.message for error in errors]


def _validate_manifest_requirements(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    auth = manifest.get("auth", {})
    auth_type = auth.get("type")
    if auth_type == "oauth2":
        if not auth.get("token_url"):
            errors.append("OAuth2 connectors must define auth.token_url")
        scopes = auth.get("scopes") or []
        if not scopes:
            errors.append("OAuth2 connectors must define auth.scopes")
    fields = auth.get("fields") or []
    if not fields:
        errors.append("Auth fields must not be empty")
    sync = manifest.get("sync", {})
    if sync.get("rate_limit_per_minute") is None:
        errors.append("sync.rate_limit_per_minute is required for certification")
    return errors


def _load_required_fields(target: str) -> list[str]:
    schema_path = DATA_SCHEMA_DIR / f"{target}.schema.json"
    if not schema_path.exists():
        return []
    schema = json.loads(schema_path.read_text())
    return list(schema.get("required", []))


def _validate_mappings(connector_root: Path, mappings: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for mapping in mappings:
        mapping_file = connector_root / mapping["mapping_file"]
        if not mapping_file.exists():
            errors.append(f"Missing mapping file: {mapping_file}")
            continue
        mapping_data = yaml.safe_load(mapping_file.read_text())
        target = mapping_data.get("target") or mapping.get("target")
        required_fields = _load_required_fields(target)
        mapped_targets = {entry.get("target") for entry in mapping_data.get("fields", [])}
        missing = [
            field
            for field in required_fields
            if field != "tenant_id" and field not in mapped_targets
        ]
        if missing:
            errors.append(
                f"Mapping {mapping_file} missing required targets: {', '.join(sorted(missing))}"
            )
    return errors


def _run_contract_tests(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return {
        "command": " ".join(command),
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "status": "passed" if result.returncode == 0 else "failed",
    }


def certify_connectors(run_tests: bool) -> dict[str, Any]:
    registry = _load_registry()
    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))
    results: list[CertificationResult] = []

    for entry in registry:
        status = entry.get("status", "unknown")
        if status not in CERTIFIABLE_STATUSES:
            continue
        manifest_path = REPO_ROOT / entry["manifest_path"]
        manifest = _load_manifest(manifest_path)
        errors = []
        errors.extend(_validate_manifest_schema(validator, manifest))
        errors.extend(_validate_manifest_requirements(manifest))
        errors.extend(_validate_mappings(manifest_path.parent, manifest.get("mappings", [])))
        results.append(
            CertificationResult(
                connector_id=entry["id"],
                status=status,
                certification=entry.get("certification", "unknown"),
                errors=errors,
            )
        )

    report: dict[str, Any] = {
        "summary": {
            "total": len(results),
            "failed": sum(1 for result in results if result.errors),
            "passed": sum(1 for result in results if not result.errors),
        },
        "connectors": [
            {
                "id": result.connector_id,
                "status": result.status,
                "certification": result.certification,
                "errors": result.errors,
                "passed": not result.errors,
            }
            for result in results
        ],
    }

    if run_tests:
        report["contract_tests"] = _run_contract_tests(
            ["pytest", "tests/integration", "-k", "connector", "-v"]
        )
    return report


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run connector certification automation.")
    parser.add_argument(
        "--output",
        type=str,
        default="artifacts/connector-certification-report.json",
        help="Path to write certification report JSON.",
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run connector contract tests (pytest).",
    )
    args = parser.parse_args()

    report = certify_connectors(args.run_tests)
    output_path = REPO_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2))

    failed = report["summary"]["failed"]
    if args.run_tests and report.get("contract_tests", {}).get("status") == "failed":
        failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
