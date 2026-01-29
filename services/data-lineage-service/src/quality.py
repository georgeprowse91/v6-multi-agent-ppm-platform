from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class QualityResult:
    score: float
    dimensions: dict[str, float]
    rules_checked: list[str]
    issues: list[dict[str, Any]]
    computed_at: str


def _get_field_value(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _check_pass(value: Any, check: dict[str, Any]) -> bool:
    check_type = check.get("type")
    if check_type == "required":
        return value is not None and value != ""
    if check_type == "min":
        if value is None:
            return False
        return float(value) >= float(check.get("value", 0))
    if check_type == "enum":
        return value in check.get("values", [])
    if check_type == "datetime":
        if not value:
            return False
        try:
            if isinstance(value, str) and value.endswith("Z"):
                value = value.replace("Z", "+00:00")
            datetime.fromisoformat(str(value))
            return True
        except ValueError:
            return False
    return False


def _dimension_for_check(check_type: str) -> str:
    if check_type == "required":
        return "completeness"
    if check_type in {"min", "enum"}:
        return "validity"
    if check_type == "datetime":
        return "timeliness"
    return "consistency"


def compute_quality(
    *,
    entity_type: str,
    entity_payload: dict[str, Any],
    rules_config: dict[str, Any],
) -> QualityResult | None:
    rules = [rule for rule in rules_config.get("rules", []) if rule.get("entity") == entity_type]
    if not rules:
        return None

    weights = rules_config.get("scoring", {}).get(
        "weights",
        {"completeness": 0.4, "validity": 0.3, "consistency": 0.2, "timeliness": 0.1},
    )
    totals = {dim: 0 for dim in weights}
    passed = {dim: 0 for dim in weights}
    issues: list[dict[str, Any]] = []
    rules_checked: list[str] = []

    for rule in rules:
        rules_checked.append(rule.get("id", "unknown"))
        for check in rule.get("checks", []):
            check_type = check.get("type", "")
            dimension = _dimension_for_check(check_type)
            totals.setdefault(dimension, 0)
            passed.setdefault(dimension, 0)
            field = check.get("field", "")
            value = _get_field_value(entity_payload, field)
            if _check_pass(value, check):
                passed[dimension] += 1
            else:
                issues.append(
                    {
                        "rule_id": rule.get("id"),
                        "field": field,
                        "check": check_type,
                        "message": rule.get("description"),
                    }
                )
            totals[dimension] += 1

    dimension_scores: dict[str, float] = {}
    for dimension, weight in weights.items():
        total = totals.get(dimension, 0)
        if total == 0:
            dimension_scores[dimension] = 1.0
        else:
            dimension_scores[dimension] = passed.get(dimension, 0) / total

    weighted_total = sum(weights.values()) or 1.0
    score = sum(dimension_scores[dim] * weights.get(dim, 0) for dim in dimension_scores)
    score = score / weighted_total

    return QualityResult(
        score=round(score, 4),
        dimensions=dimension_scores,
        rules_checked=rules_checked,
        issues=issues,
        computed_at=datetime.utcnow().isoformat(),
    )
