#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
_COMMON_SRC = REPO_ROOT / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402
ensure_monorepo_paths(REPO_ROOT)

from connectors.sdk.connector_maturity_inventory import build_inventory

DEFAULT_POLICY_PATH = REPO_ROOT / "ops" / "config" / "connector_maturity_policy.yaml"


@dataclass(frozen=True)
class Violation:
    rule_id: str
    message: str
    connector_id: str | None = None


def _load_policy(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text()) or {}


def _load_inventory(path: Path | None) -> dict[str, Any]:
    if path is None:
        return build_inventory()
    return json.loads(path.read_text())


def _exception_index(policy: dict[str, Any]) -> tuple[dict[tuple[str, str], date], list[Violation]]:
    index: dict[tuple[str, str], date] = {}
    violations: list[Violation] = []
    today = date.today()
    for entry in policy.get("exceptions", []):
        connector_id = entry.get("connector_id")
        rule_id = entry.get("rule_id")
        expires_on = entry.get("expires_on")
        if not connector_id or not rule_id or not expires_on:
            violations.append(
                Violation(
                    rule_id="invalid_exception",
                    connector_id=connector_id,
                    message=f"Exception is missing connector_id/rule_id/expires_on: {entry!r}",
                )
            )
            continue
        try:
            expiry = date.fromisoformat(str(expires_on))
        except ValueError:
            violations.append(
                Violation(
                    rule_id="invalid_exception",
                    connector_id=connector_id,
                    message=f"Exception {connector_id}/{rule_id} has invalid expires_on '{expires_on}'",
                )
            )
            continue
        if expiry < today:
            violations.append(
                Violation(
                    rule_id="expired_exception",
                    connector_id=connector_id,
                    message=f"Exception {connector_id}/{rule_id} expired on {expiry.isoformat()}",
                )
            )
            continue
        index[(connector_id, rule_id)] = expiry

    return index, violations


def _is_waived(violation: Violation, exception_index: dict[tuple[str, str], date]) -> bool:
    if not violation.connector_id:
        return False
    return (violation.connector_id, violation.rule_id) in exception_index


def _evaluate(
    policy: dict[str, Any], inventory: dict[str, Any]
) -> tuple[list[Violation], list[Violation]]:
    thresholds = policy.get("thresholds", {})
    violations: list[Violation] = []

    mappings_threshold = thresholds.get("mappings", {})
    mappings_rule_id = mappings_threshold.get("rule_id", "missing_manifest_mappings")
    max_missing_mappings = int(mappings_threshold.get("max_missing_connectors", 0))
    missing_mappings = sorted(inventory.get("gaps", {}).get("incomplete_mapping", []))

    for connector_id in missing_mappings:
        violations.append(
            Violation(
                rule_id=mappings_rule_id,
                connector_id=connector_id,
                message=f"{connector_id} has missing manifest mapping files",
            )
        )

    tier1_threshold = thresholds.get("tier1", {})
    max_business_priority = int(tier1_threshold.get("max_business_priority", 5))
    required_capabilities = list(tier1_threshold.get("required_capabilities", []))
    tier1_rule_id = "tier1_required_capabilities"

    for connector in inventory.get("connectors", []):
        connector_id = connector.get("id")
        business_priority = int(connector.get("business_priority", 999))
        if business_priority > max_business_priority:
            continue
        coverage = connector.get("coverage", {})
        missing_required = [cap for cap in required_capabilities if not bool(coverage.get(cap))]
        if missing_required:
            violations.append(
                Violation(
                    rule_id=tier1_rule_id,
                    connector_id=connector_id,
                    message=(
                        f"{connector_id} (priority {business_priority}) missing required capabilities: "
                        + ", ".join(missing_required)
                    ),
                )
            )

    exception_index, exception_violations = _exception_index(policy)
    effective_violations = [v for v in violations if not _is_waived(v, exception_index)]

    non_waived_mapping_count = sum(1 for v in effective_violations if v.rule_id == mappings_rule_id)
    if non_waived_mapping_count > max_missing_mappings:
        effective_violations.append(
            Violation(
                rule_id=mappings_rule_id,
                message=(
                    "Missing manifest mappings threshold exceeded: "
                    f"{non_waived_mapping_count} > {max_missing_mappings}"
                ),
            )
        )

    return effective_violations, exception_violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate connector maturity policy thresholds")
    parser.add_argument(
        "--policy",
        type=Path,
        default=DEFAULT_POLICY_PATH,
        help="Path to connector maturity policy YAML",
    )
    parser.add_argument(
        "--inventory-json",
        type=Path,
        default=None,
        help="Optional precomputed inventory JSON file; defaults to generating from manifests",
    )
    args = parser.parse_args()

    policy = _load_policy(args.policy)
    inventory = _load_inventory(args.inventory_json)

    threshold_violations, exception_violations = _evaluate(policy, inventory)
    failures = [*exception_violations, *threshold_violations]

    if failures:
        print("Connector maturity policy validation failed:")
        for failure in failures:
            prefix = f"[{failure.rule_id}]"
            connector = f"[{failure.connector_id}] " if failure.connector_id else ""
            print(f" - {prefix} {connector}{failure.message}")
        return 1

    print("Connector maturity policy validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
