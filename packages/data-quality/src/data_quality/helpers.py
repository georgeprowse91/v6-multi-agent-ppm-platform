from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from data_quality.rules import DataQualityIssue
from data_quality.schema_validation import SchemaValidationError, validate_instance


@dataclass(frozen=True)
class RuleSetResult:
    issues: tuple[DataQualityIssue, ...]

    @property
    def is_valid(self) -> bool:
        return not self.issues


def validate_against_schema(
    schema_path: str | Path, payload: dict[str, Any]
) -> list[SchemaValidationError]:
    return validate_instance(payload, Path(schema_path))


def _get_value(payload: dict[str, Any], field_path: str) -> Any:
    current: Any = payload
    for part in field_path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _load_rule_set(rule_set: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(rule_set, dict):
        return rule_set
    path = Path(rule_set)
    return yaml.safe_load(path.read_text())


def apply_rule_set(rule_set: dict[str, Any] | str | Path, payload: dict[str, Any]) -> RuleSetResult:
    rule_data = _load_rule_set(rule_set)
    issues: list[DataQualityIssue] = []

    for rule in rule_data.get("rules", []):
        rule_id = rule.get("id", "unknown")
        for check in rule.get("checks", []):
            field = check.get("field", "")
            check_type = check.get("type")
            value = _get_value(payload, field)

            if check_type == "required" and (value is None or value == ""):
                issues.append(
                    DataQualityIssue(
                        rule_id=rule_id,
                        message=f"{field} is required",
                        severity="error",
                        record_id=None,
                    )
                )
            elif check_type == "min":
                minimum = check.get("value")
                if value is None or minimum is None or value < minimum:
                    issues.append(
                        DataQualityIssue(
                            rule_id=rule_id,
                            message=f"{field} must be >= {minimum}",
                            severity="error",
                            record_id=None,
                        )
                    )
            elif check_type == "enum":
                values = check.get("values", [])
                if value not in values:
                    issues.append(
                        DataQualityIssue(
                            rule_id=rule_id,
                            message=f"{field} must be one of {values}",
                            severity="error",
                            record_id=None,
                        )
                    )
            elif check_type == "datetime":
                try:
                    if value:
                        datetime.fromisoformat(value)
                except (TypeError, ValueError):
                    issues.append(
                        DataQualityIssue(
                            rule_id=rule_id,
                            message=f"{field} must be ISO 8601 datetime",
                            severity="error",
                            record_id=None,
                        )
                    )

    return RuleSetResult(issues=tuple(issues))
