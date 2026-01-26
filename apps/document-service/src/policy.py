from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("document-policy")
DEFAULT_POLICY_BUNDLE_PATH = (
    Path(__file__).resolve().parents[1] / "policies" / "bundles" / "default-policy-bundle.yaml"
)


class PolicyDecision:
    def __init__(self, decision: str, reasons: list[str], advisories: list[str]) -> None:
        self.decision = decision
        self.reasons = reasons
        self.advisories = advisories


def _load_policy_bundle() -> dict[str, Any]:
    bundle_path = Path(DEFAULT_POLICY_BUNDLE_PATH)
    return yaml.safe_load(bundle_path.read_text())


def _get_field(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _apply_rule(document: dict[str, Any], rule: dict[str, Any]) -> bool:
    value = _get_field(document, rule.get("field", ""))
    operator = rule.get("operator")
    expected = rule.get("value")
    if operator == "equals":
        return value == expected
    if operator == "gte":
        try:
            return float(value) >= float(expected)
        except (TypeError, ValueError):
            return False
    return True


def evaluate_document_policy(document: dict[str, Any]) -> PolicyDecision:
    bundle = _load_policy_bundle()
    decision = "allow"
    reasons: list[str] = []
    advisories: list[str] = []

    for policy in bundle.get("policies", []):
        for rule in policy.get("rules", []):
            if not _apply_rule(document, rule):
                message = f"{policy.get('id')}: {policy.get('name')}"
                if policy.get("enforcement") == "blocking":
                    decision = "deny"
                    reasons.append(message)
                else:
                    advisories.append(message)

    logger.info("document_policy_evaluated", extra={"decision": decision})
    return PolicyDecision(decision=decision, reasons=reasons, advisories=advisories)
