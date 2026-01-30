from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any, Callable

from data_quality.rules import DataQualityIssue, DataQualityReport


@dataclass(frozen=True)
class RemediationAction:
    rule_id: str
    field: str
    previous_value: Any
    new_value: Any
    reason: str


@dataclass(frozen=True)
class RemediationResult:
    record_type: str
    record_id: str | None
    original_payload: dict[str, Any]
    remediated_payload: dict[str, Any]
    actions: tuple[RemediationAction, ...] = field(default_factory=tuple)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _ensure_iso_date(value: date | None) -> str | None:
    if not value:
        return None
    return value.isoformat()


def _ensure_iso_datetime() -> str:
    return datetime.utcnow().isoformat()


def _apply_action(
    payload: dict[str, Any],
    actions: list[RemediationAction],
    *,
    rule_id: str,
    field: str,
    new_value: Any,
    reason: str,
) -> None:
    previous = payload.get(field)
    payload[field] = new_value
    actions.append(
        RemediationAction(
            rule_id=rule_id,
            field=field,
            previous_value=previous,
            new_value=new_value,
            reason=reason,
        )
    )


def _fix_project_dates(payload: dict[str, Any], actions: list[RemediationAction]) -> None:
    start = _parse_date(payload.get("start_date"))
    end = _parse_date(payload.get("end_date"))
    if start and end and end < start:
        _apply_action(
            payload,
            actions,
            rule_id="project_dates",
            field="end_date",
            new_value=_ensure_iso_date(start),
            reason="Adjusted end_date to match start_date.",
        )


def _fix_project_closed_end_date(payload: dict[str, Any], actions: list[RemediationAction]) -> None:
    if payload.get("status") == "closed" and not payload.get("end_date"):
        _apply_action(
            payload,
            actions,
            rule_id="project_closed_end_date",
            field="end_date",
            new_value=_ensure_iso_date(date.today()),
            reason="Filled end_date for closed project.",
        )


def _fix_budget_amount(payload: dict[str, Any], actions: list[RemediationAction]) -> None:
    amount = payload.get("amount")
    if amount is not None and amount <= 0:
        _apply_action(
            payload,
            actions,
            rule_id="budget_amount",
            field="amount",
            new_value=abs(float(amount)) or 1.0,
            reason="Adjusted amount to positive value.",
        )


def _fix_budget_fiscal_year(payload: dict[str, Any], actions: list[RemediationAction]) -> None:
    fiscal_year = payload.get("fiscal_year")
    if fiscal_year is not None and not (2020 <= fiscal_year <= 2100):
        _apply_action(
            payload,
            actions,
            rule_id="budget_fiscal_year",
            field="fiscal_year",
            new_value=max(2020, min(2100, int(fiscal_year))),
            reason="Clamped fiscal_year to supported range.",
        )


def _fix_due_date(payload: dict[str, Any], actions: list[RemediationAction]) -> None:
    due = _parse_date(payload.get("due_date"))
    created_at = payload.get("created_at")
    if due and created_at:
        try:
            created = datetime.fromisoformat(str(created_at)).date()
        except ValueError:
            return
        if due < created:
            _apply_action(
                payload,
                actions,
                rule_id="work_item_due",
                field="due_date",
                new_value=_ensure_iso_date(created),
                reason="Aligned due_date with created_at.",
            )


def _fix_updated_at(payload: dict[str, Any], actions: list[RemediationAction], rule_id: str) -> None:
    if not payload.get("updated_at"):
        _apply_action(
            payload,
            actions,
            rule_id=rule_id,
            field="updated_at",
            new_value=_ensure_iso_datetime(),
            reason="Added updated_at timestamp.",
        )


def _fix_issue_closed(payload: dict[str, Any], actions: list[RemediationAction]) -> None:
    if payload.get("status") in {"resolved", "closed"}:
        _fix_updated_at(payload, actions, "issue_closed")


def _fix_risk_closed(payload: dict[str, Any], actions: list[RemediationAction]) -> None:
    if payload.get("status") in {"mitigated", "closed"}:
        _fix_updated_at(payload, actions, "risk_closed")


def _fix_work_item_done(payload: dict[str, Any], actions: list[RemediationAction]) -> None:
    if payload.get("status") == "done":
        _fix_updated_at(payload, actions, "work_item_done")


REMEDIATION_HANDLERS: dict[str, Callable[[dict[str, Any], list[RemediationAction]], None]] = {
    "project_dates": _fix_project_dates,
    "project_closed_end_date": _fix_project_closed_end_date,
    "budget_amount": _fix_budget_amount,
    "budget_fiscal_year": _fix_budget_fiscal_year,
    "work_item_due": _fix_due_date,
    "work_item_done": _fix_work_item_done,
    "issue_closed": _fix_issue_closed,
    "risk_closed": _fix_risk_closed,
}


def remediate_payload(
    record_type: str,
    record: dict[str, Any],
    report: DataQualityReport | None = None,
) -> RemediationResult:
    working = dict(record)
    actions: list[RemediationAction] = []

    issues = report.issues if report else tuple()
    for issue in issues:
        handler = REMEDIATION_HANDLERS.get(issue.rule_id)
        if handler:
            handler(working, actions)

    return RemediationResult(
        record_type=record_type,
        record_id=record.get("id"),
        original_payload=record,
        remediated_payload=working,
        actions=tuple(actions),
    )


def remediate_from_issues(
    record_type: str,
    record: dict[str, Any],
    issues: list[DataQualityIssue],
) -> RemediationResult:
    report = DataQualityReport(record_type=record_type, record_id=record.get("id"), issues=tuple(issues))
    return remediate_payload(record_type, record, report)
