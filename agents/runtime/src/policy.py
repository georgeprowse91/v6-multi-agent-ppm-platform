from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml
from feature_flags import is_feature_enabled

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


@dataclass(frozen=True)
class ComplianceDecision:
    decision: str
    reasons: tuple[str, ...]
    sanitized_payload: dict[str, Any]
    masked_fields: tuple[str, ...]


_APPROVAL_CHANGE_TYPES = {
    "budget",
    "budget_change",
    "resource",
    "resource_change",
    "scope",
    "scope_change",
}

_PERSONAL_DATA_FIELDS = {
    "email",
    "phone",
    "address",
    "ssn",
    "dob",
    "date_of_birth",
    "medical_record",
}

_MASKED_PERSONAL_DATA_FIELDS = {"email", "phone", "address", "ssn", "dob", "date_of_birth"}


def _mask_value(value: Any) -> str:
    raw = str(value or "")
    if not raw:
        return "***"
    if len(raw) <= 4:
        return "*" * len(raw)
    return f"{raw[:2]}***{raw[-2:]}"


def evaluate_compliance_controls(
    payload: dict[str, Any],
    *,
    required_fields: set[str] | None = None,
) -> ComplianceDecision:
    """Apply data-minimization and consent checks to a payload.

    - Removes unexpected fields from `payload["personal_data"]`.
    - Masks selected personal data fields for downstream processing.
    - Requires consent for any personal data processing.
    """
    reasons: list[str] = []
    masked_fields: list[str] = []
    sanitized = dict(payload)
    personal_data = payload.get("personal_data")
    if not isinstance(personal_data, dict):
        return ComplianceDecision(
            decision="allow",
            reasons=tuple(reasons),
            sanitized_payload=sanitized,
            masked_fields=tuple(masked_fields),
        )

    allowed_fields = required_fields or _PERSONAL_DATA_FIELDS
    minimized_data: dict[str, Any] = {}
    for key, value in personal_data.items():
        if key not in allowed_fields:
            reasons.append(f"data_minimization_removed:{key}")
            continue
        if key in _MASKED_PERSONAL_DATA_FIELDS:
            minimized_data[key] = _mask_value(value)
            masked_fields.append(key)
            continue
        minimized_data[key] = value

    consent = payload.get("consent")
    consent_granted = isinstance(consent, dict) and bool(consent.get("granted"))
    if minimized_data and not consent_granted:
        reasons.append("consent_missing")
        return ComplianceDecision(
            decision="deny",
            reasons=tuple(reasons),
            sanitized_payload={"error": "Consent is required before processing personal data."},
            masked_fields=tuple(masked_fields),
        )

    sanitized["personal_data"] = minimized_data
    return ComplianceDecision(
        decision="allow",
        reasons=tuple(reasons),
        sanitized_payload=sanitized,
        masked_fields=tuple(masked_fields),
    )


def _normalize_change_type(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized or None
    return None


def _extract_change_type(bundle: dict[str, Any]) -> str | None:
    for path in (
        "change.type",
        "change_type",
        "request_type",
        "payload.change_type",
        "payload.request_type",
        "metadata.change_type",
        "metadata.request_type",
    ):
        value = _get_field(bundle, path) if "." in path else bundle.get(path)
        normalized = _normalize_change_type(value)
        if normalized:
            return normalized
    for key in _APPROVAL_CHANGE_TYPES:
        if key in bundle and bundle.get(key):
            return key
    return None


def _parse_approval_state(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"approved", "approve", "accepted", "allow", "allowed", "success"}:
            return True
        if normalized in {"rejected", "reject", "denied", "deny", "declined", "failed"}:
            return False
    return None


def _approval_granted(bundle: dict[str, Any]) -> bool:
    candidates = [
        "approval.status",
        "approval.decision",
        "approval.state",
        "approval.outcome",
        "approval_status",
        "approval_decision",
        "approval",
    ]
    for path in candidates:
        value = _get_field(bundle, path) if "." in path else bundle.get(path)
        if isinstance(value, dict):
            for inner_key in ("status", "decision", "state", "outcome"):
                parsed = _parse_approval_state(value.get(inner_key))
                if parsed is not None:
                    return parsed
        parsed = _parse_approval_state(value)
        if parsed is not None:
            return parsed
    return False


def _approval_enforcement_enabled() -> bool:
    environment = os.getenv("ENVIRONMENT", "dev")
    return not is_feature_enabled("autonomous_approvals", environment=environment, default=False)


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
        if not isinstance(value, (int, float, str)) or not isinstance(expected, (int, float, str)):
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
                errors.append(f"policies[{idx}].rules[{ridx}]: unknown operator '{op}'")
            if "field" not in rule:
                errors.append(f"policies[{idx}].rules[{ridx}]: missing required field 'field'")

    return errors


def evaluate_policy_bundle(bundle: dict[str, Any], policy_bundle: dict[str, Any]) -> PolicyDecision:
    reasons: list[str] = []
    decision = "allow"
    policies = policy_bundle.get("policies", [])
    requires_approval = False

    for policy in policies:
        rules = policy.get("rules", [])
        for rule in rules:
            if not _apply_rule(bundle, rule):
                message = f"{policy.get('id')}: {policy.get('name')}"
                reasons.append(message)
                if policy.get("enforcement") == "blocking":
                    decision = "deny"

    if decision != "deny" and _approval_enforcement_enabled():
        change_type = _extract_change_type(bundle)
        if change_type and change_type in _APPROVAL_CHANGE_TYPES:
            if not _approval_granted(bundle):
                requires_approval = True
                reasons.append(f"approval_required: {change_type.replace('_', ' ')} change")

    if requires_approval:
        return PolicyDecision(decision="approval_required", reasons=tuple(reasons))

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
