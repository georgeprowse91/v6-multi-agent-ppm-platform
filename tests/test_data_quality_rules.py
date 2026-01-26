from __future__ import annotations

from data_quality.rules import evaluate_quality_rules


def test_project_date_rules() -> None:
    record = {
        "id": "proj-1",
        "tenant_id": "tenant-a",
        "program_id": "prog-1",
        "name": "Migration",
        "status": "closed",
        "start_date": "2024-05-01",
        "end_date": "2024-04-01",
        "owner": "pm",
        "classification": "internal",
        "created_at": "2024-05-01T12:00:00+00:00",
    }

    report = evaluate_quality_rules("project", record)

    rule_ids = {issue.rule_id for issue in report.issues}
    assert "project_dates" in rule_ids
    assert "project_closed_end_date" not in rule_ids


def test_budget_rules() -> None:
    record = {
        "id": "budget-1",
        "tenant_id": "tenant-a",
        "portfolio_id": "port-1",
        "name": "Core",
        "currency": "USD",
        "amount": 0,
        "fiscal_year": 2019,
        "status": "draft",
        "owner": "cfo",
        "classification": "internal",
        "created_at": "2024-01-01T00:00:00+00:00",
    }

    report = evaluate_quality_rules("budget", record)
    rule_ids = {issue.rule_id for issue in report.issues}

    assert "budget_amount" in rule_ids
    assert "budget_fiscal_year" in rule_ids


def test_schema_and_status_rules() -> None:
    record = {
        "id": "issue-1",
        "tenant_id": "tenant-a",
        "title": "Latency",
        "severity": "high",
        "status": "resolved",
        "project_id": "proj-1",
        "owner": "owner",
        "classification": "internal",
        "created_at": "2024-01-01T00:00:00+00:00",
    }

    report = evaluate_quality_rules("issue", record)

    rule_ids = {issue.rule_id for issue in report.issues}
    assert "issue_closed" in rule_ids
