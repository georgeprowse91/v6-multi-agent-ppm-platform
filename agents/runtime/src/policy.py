from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

logger = logging.getLogger("agents.runtime.policy")

DEFAULT_POLICY_BUNDLE_PATH = (
    Path(__file__).resolve().parents[3]
    / "services"
    / "policy-engine"
    / "policies"
    / "bundles"
    / "default-policy-bundle.yaml"
)

_VALID_OPERATORS = frozenset({"equals", "not_equals", "contains", "not_contains", "gte", "lte"})


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
        return bool(value == expected)
    if operator == "not_equals":
        return bool(value != expected)
    if operator == "contains":
        return str(expected or "") in str(value or "")
    if operator == "not_contains":
        return str(expected or "") not in str(value or "")
    if operator in {"gte", "lte"}:
        if value is None or expected is None:
            return False
        if not isinstance(value, (int, float, str)) or not isinstance(
            expected, (int, float, str)
        ):
            return False
        try:
            current = float(value)
            target = float(expected)
        except (TypeError, ValueError):
            return False
        return current >= target if operator == "gte" else current <= target
    return False


def validate_policy_bundle(policy_bundle: dict[str, Any]) -> list[str]:
    """Validate structure of a policy bundle and return a list of error messages.

    Returns an empty list when the bundle is valid.
    """
    errors: list[str] = []
    if not isinstance(policy_bundle, dict):
        return ["Policy bundle must be a mapping"]

    policies = policy_bundle.get("policies")
    if policies is None:
        return []  # No policies is valid (permissive default)
    if not isinstance(policies, list):
        return ["'policies' must be a list"]

    for idx, policy in enumerate(policies):
        if not isinstance(policy, dict):
            errors.append(f"policies[{idx}]: must be a mapping")
            continue
        if "id" not in policy:
            errors.append(f"policies[{idx}]: missing required field 'id'")
        enforcement = policy.get("enforcement")
        if enforcement and enforcement not in {"blocking", "advisory"}:
            errors.append(
                f"policies[{idx}]: enforcement must be 'blocking' or 'advisory', got '{enforcement}'"
            )
        rules = policy.get("rules", [])
        if not isinstance(rules, list):
            errors.append(f"policies[{idx}]: 'rules' must be a list")
            continue
        for ridx, rule in enumerate(rules):
            if not isinstance(rule, dict):
                errors.append(f"policies[{idx}].rules[{ridx}]: must be a mapping")
                continue
            op = rule.get("operator")
            if op and op not in _VALID_OPERATORS:
                errors.append(
                    f"policies[{idx}].rules[{ridx}]: unknown operator '{op}'"
                )
            if "field" not in rule:
                errors.append(f"policies[{idx}].rules[{ridx}]: missing required field 'field'")

    return errors


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


# Cache the default bundle to avoid re-reading the file on every request
_DEFAULT_BUNDLE_CACHE: dict[str, Any] | None = None


def load_default_policy_bundle(path: Path | None = None) -> dict[str, Any]:
    global _DEFAULT_BUNDLE_CACHE
    bundle_path = path or DEFAULT_POLICY_BUNDLE_PATH

    if path is None and _DEFAULT_BUNDLE_CACHE is not None:
        return _DEFAULT_BUNDLE_CACHE

    try:
        raw = bundle_path.read_text()
    except OSError as exc:
        logger.warning(
            "policy_bundle_load_failed",
            extra={"path": str(bundle_path), "error": str(exc)},
        )
        # Return a permissive empty bundle rather than crashing
        return {"policies": []}

    data = cast(dict[str, Any], yaml.safe_load(raw))
    if not isinstance(data, dict):
        logger.warning("policy_bundle_invalid", extra={"path": str(bundle_path)})
        return {"policies": []}

    errors = validate_policy_bundle(data)
    if errors:
        logger.warning(
            "policy_bundle_validation_warnings",
            extra={"path": str(bundle_path), "errors": errors},
        )

    if path is None:
        _DEFAULT_BUNDLE_CACHE = data
    return data
