from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_POLICY_BUNDLE_PATH = (
    Path(__file__).resolve().parents[3]
    / "services"
    / "policy-engine"
    / "policies"
    / "bundles"
    / "default-policy-bundle.yaml"
)


@dataclass(frozen=True)
class PolicyDecision:
    decision: str
    reasons: tuple[str, ...]


def _get_field(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _apply_rule(bundle: dict[str, Any], rule: dict[str, Any]) -> bool:
    value = _get_field(bundle, rule.get("field", ""))
    operator = rule.get("operator")
    expected = rule.get("value")
    if operator == "equals":
        return value == expected
    if operator == "not_equals":
        return value != expected
    if operator == "contains":
        return expected in str(value or "")
    if operator == "not_contains":
        return expected not in str(value or "")
    if operator in {"gte", "lte"}:
        try:
            current = float(value)
            target = float(expected)
        except (TypeError, ValueError):
            return False
        return current >= target if operator == "gte" else current <= target
    return False


def evaluate_policy_bundle(bundle: dict[str, Any], policy_bundle: dict[str, Any]) -> PolicyDecision:
    reasons: list[str] = []
    decision = "allow"
    policies = policy_bundle.get("policies", [])

    for policy in policies:
        rules = policy.get("rules", [])
        for rule in rules:
            if not _apply_rule(bundle, rule):
                message = f"{policy.get('id')}: {policy.get('name')}"
                reasons.append(message)
                if policy.get("enforcement") == "blocking":
                    decision = "deny"

    return PolicyDecision(decision=decision, reasons=tuple(reasons))


def load_default_policy_bundle(path: Path | None = None) -> dict[str, Any]:
    bundle_path = path or DEFAULT_POLICY_BUNDLE_PATH
    return yaml.safe_load(bundle_path.read_text())
