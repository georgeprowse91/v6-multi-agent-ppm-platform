from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

from data_quality.schema_validation import validate_instance

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_DIR = REPO_ROOT / "data" / "schemas"


@dataclass(frozen=True)
class DataQualityIssue:
    rule_id: str
    message: str
    severity: str
    record_id: str | None = None


@dataclass(frozen=True)
class DataQualityReport:
    record_type: str
    record_id: str | None
    issues: tuple[DataQualityIssue, ...] = field(default_factory=tuple)

    @property
    def is_valid(self) -> bool:
        return not self.issues


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _schema_path(record_type: str) -> Path:
    return SCHEMA_DIR / f"{record_type}.schema.json"


def _schema_issues(record_type: str, record: dict[str, Any]) -> list[DataQualityIssue]:
    errors = validate_instance(record, _schema_path(record_type))
    return [
        DataQualityIssue(
            rule_id="schema",
            message=f"{error.path}: {error.message}",
            severity="error",
            record_id=record.get("id"),
        )
        for error in errors
    ]


def _rule_issue(rule_id: str, message: str, record: dict[str, Any]) -> DataQualityIssue:
    return DataQualityIssue(
        rule_id=rule_id,
        message=message,
        severity="error",
        record_id=record.get("id"),
    )


def _validate_project(record: dict[str, Any]) -> list[DataQualityIssue]:
    issues: list[DataQualityIssue] = []
    start = _parse_date(record.get("start_date"))
    end = _parse_date(record.get("end_date"))
    if start and end and end < start:
        issues.append(_rule_issue("project_dates", "end_date must be after start_date", record))
    if record.get("status") == "closed" and not end:
        issues.append(_rule_issue("project_closed_end_date", "closed projects require end_date", record))
    return issues


def _validate_budget(record: dict[str, Any]) -> list[DataQualityIssue]:
    issues: list[DataQualityIssue] = []
    amount = record.get("amount")
    if amount is not None and amount <= 0:
        issues.append(_rule_issue("budget_amount", "amount must be greater than zero", record))
    fiscal_year = record.get("fiscal_year")
    if fiscal_year is not None and not (2020 <= fiscal_year <= 2100):
        issues.append(_rule_issue("budget_fiscal_year", "fiscal_year must be between 2020 and 2100", record))
    return issues


def _validate_work_item(record: dict[str, Any]) -> list[DataQualityIssue]:
    issues: list[DataQualityIssue] = []
    due_date = _parse_date(record.get("due_date"))
    created_at = _parse_datetime(record.get("created_at"))
    if due_date and created_at and due_date < created_at.date():
        issues.append(
            _rule_issue("work_item_due", "due_date must be on or after created_at", record)
        )
    if record.get("status") == "done" and not record.get("updated_at"):
        issues.append(
            _rule_issue("work_item_done", "done work items require updated_at", record)
        )
    return issues


def _validate_issue(record: dict[str, Any]) -> list[DataQualityIssue]:
    issues: list[DataQualityIssue] = []
    if record.get("status") in {"resolved", "closed"} and not record.get("updated_at"):
        issues.append(_rule_issue("issue_closed", "resolved issues require updated_at", record))
    return issues


def _validate_risk(record: dict[str, Any]) -> list[DataQualityIssue]:
    issues: list[DataQualityIssue] = []
    if record.get("status") in {"mitigated", "closed"} and not record.get("updated_at"):
        issues.append(_rule_issue("risk_closed", "mitigated risks require updated_at", record))
    return issues


def evaluate_quality_rules(
    record_type: str, record: dict[str, Any]
) -> DataQualityReport:
    issues: list[DataQualityIssue] = []
    issues.extend(_schema_issues(record_type, record))

    if record_type == "project":
        issues.extend(_validate_project(record))
    elif record_type == "budget":
        issues.extend(_validate_budget(record))
    elif record_type == "work-item":
        issues.extend(_validate_work_item(record))
    elif record_type == "issue":
        issues.extend(_validate_issue(record))
    elif record_type == "risk":
        issues.extend(_validate_risk(record))

    return DataQualityReport(record_type=record_type, record_id=record.get("id"), issues=tuple(issues))


def evaluate_records(
    record_type: str, records: Iterable[dict[str, Any]]
) -> list[DataQualityReport]:
    return [evaluate_quality_rules(record_type, record) for record in records]
