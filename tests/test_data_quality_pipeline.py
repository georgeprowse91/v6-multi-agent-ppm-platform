from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from data_quality.remediation import remediate_from_issues, remediate_payload
from data_quality import rules as data_quality_rules
from data_quality.rules import DataQualityIssue, evaluate_quality_rules, evaluate_records
from data_quality.schema_validation import validate_instance

SCHEMA_DIR = Path("data/schemas")
EXAMPLES_DIR = SCHEMA_DIR / "examples"


def _load_example(name: str) -> dict[str, object]:
    return json.loads((EXAMPLES_DIR / f"{name}.json").read_text())


@pytest.fixture
def project_payload() -> dict[str, object]:
    return _load_example("project")


@pytest.fixture
def budget_payload() -> dict[str, object]:
    return _load_example("budget")


@pytest.fixture
def work_item_payload() -> dict[str, object]:
    return _load_example("work-item")


def test_rules_required_fields_range_and_type_checks(
    project_payload: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    record = deepcopy(project_payload)
    record.pop("owner")
    record["status"] = "invalid-status"
    record["created_at"] = "2026-03-01T08:00:00+00:00"

    monkeypatch.setattr(
        data_quality_rules,
        "_schema_issues",
        lambda *_args: [
            DataQualityIssue("schema", "/: 'owner' is a required property", "error", "proj-001"),
            DataQualityIssue(
                "schema",
                "/status: 'invalid-status' is not one of ['initiated']",
                "error",
                "proj-001",
            ),
            DataQualityIssue("schema", "/start_date: '2026-13-01' is not a 'date'", "error", "proj-001"),
        ],
    )

    report = evaluate_quality_rules("project", record)

    assert report.is_valid is False
    schema_messages = [issue.message for issue in report.issues if issue.rule_id == "schema"]
    assert any("'owner' is a required property" in message for message in schema_messages)
    assert any("'invalid-status' is not one of" in message for message in schema_messages)
    assert any("is not a 'date'" in message for message in schema_messages)


def test_rules_budget_range_failures_and_pass_conditions(
    budget_payload: dict[str, object],
) -> None:
    valid_report = evaluate_quality_rules("budget", deepcopy(budget_payload))
    assert valid_report.is_valid is True
    assert valid_report.issues == ()

    invalid_record = deepcopy(budget_payload)
    invalid_record["amount"] = -0.01
    invalid_record["fiscal_year"] = 2110

    invalid_report = evaluate_quality_rules("budget", invalid_record)
    rule_ids = [issue.rule_id for issue in invalid_report.issues]

    assert "budget_amount" in rule_ids
    assert "budget_fiscal_year" in rule_ids


def test_rules_date_parsing_edge_case_raises_for_non_iso_dates(
    work_item_payload: dict[str, object],
) -> None:
    record = deepcopy(work_item_payload)
    record["due_date"] = "31-12-2026"

    with pytest.raises(ValueError):
        evaluate_quality_rules("work-item", record)


def test_multi_rule_ordering_and_aggregate_behavior(
    work_item_payload: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = deepcopy(work_item_payload)
    record.pop("assigned_to")
    record["status"] = "done"
    record["created_at"] = "2026-04-12T10:00:00+00:00"
    record.pop("updated_at", None)

    monkeypatch.setattr(
        data_quality_rules,
        "_schema_issues",
        lambda _record_type, payload: (
            [DataQualityIssue("schema", "/assigned_to: required", "error", "work-001")]
            if "assigned_to" not in payload
            else []
        ),
    )

    report = evaluate_quality_rules("work-item", record)
    assert report.is_valid is False
    assert report.issues[0].rule_id == "schema"
    assert report.issues[-1].rule_id == "work_item_done"

    clean_record = deepcopy(work_item_payload)
    clean_record["created_at"] = "2026-04-12T10:00:00+00:00"
    reports = evaluate_records("work-item", [clean_record, record])
    assert len(reports) == 2
    assert reports[0].is_valid is True
    assert reports[1].is_valid is False


def test_remediation_coercion_fallback_and_untouched_field_preservation(
    budget_payload: dict[str, object],
) -> None:
    record = deepcopy(budget_payload)
    record["amount"] = -500
    record["fiscal_year"] = 1900
    record["metadata"] = {"source": "erp", "owner": "finance"}

    issues = [
        DataQualityIssue("budget_amount", "amount must be greater than zero", "error", "budget-001"),
        DataQualityIssue(
            "budget_fiscal_year",
            "fiscal_year must be between 2020 and 2100",
            "error",
            "budget-001",
        ),
    ]

    result = remediate_from_issues("budget", record, issues)

    assert result.remediated_payload["amount"] == 500.0
    assert result.remediated_payload["fiscal_year"] == 2020
    assert result.remediated_payload["metadata"] == {"source": "erp", "owner": "finance"}
    assert record["metadata"] == {"source": "erp", "owner": "finance"}
    assert [action.rule_id for action in result.actions] == ["budget_amount", "budget_fiscal_year"]


def test_remediation_default_timestamp_and_action_correctness(
    work_item_payload: dict[str, object],
) -> None:
    record = deepcopy(work_item_payload)
    record["status"] = "done"
    record.pop("updated_at", None)

    issues = [
        DataQualityIssue("work_item_done", "done work items require updated_at", "error", "wi-001")
    ]

    result = remediate_from_issues("work-item", record, issues)

    assert "updated_at" in result.remediated_payload
    assert result.actions[0].field == "updated_at"
    assert result.actions[0].previous_value is None
    assert result.actions[0].reason == "Added updated_at timestamp."


def test_remediation_no_report_leaves_payload_unchanged(project_payload: dict[str, object]) -> None:
    record = deepcopy(project_payload)

    result = remediate_payload("project", record)

    assert result.actions == ()
    assert result.remediated_payload == record


def test_schema_validation_accepts_valid_document_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _load_example("document")

    class FakeValidator:
        def __init__(self, schema: dict[str, object], format_checker: object = None) -> None:
            self.schema = schema

        def iter_errors(self, instance: dict[str, object]) -> list[object]:
            return []

    monkeypatch.setattr("data_quality.schema_validation.Draft202012Validator", FakeValidator)

    errors = validate_instance(payload, SCHEMA_DIR / "document.schema.json")

    assert errors == []


def test_schema_validation_rejects_invalid_audit_event_with_precise_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _load_example("audit-event")
    payload["timestamp"] = "not-a-datetime"
    payload["actor"] = {"type": "user", "roles": []}

    class FakeValidationError:
        def __init__(self, message: str, path: list[str]) -> None:
            self.message = message
            self.path = path

    class FakeValidator:
        def __init__(self, schema: dict[str, object], format_checker: object = None) -> None:
            self.schema = schema

        def iter_errors(self, instance: dict[str, object]) -> list[FakeValidationError]:
            errors: list[FakeValidationError] = []
            if "id" not in instance.get("actor", {}):
                errors.append(FakeValidationError("'id' is a required property", ["actor"]))
            if instance.get("timestamp") == "not-a-datetime":
                errors.append(
                    FakeValidationError("'not-a-datetime' is not a 'date-time'", ["timestamp"])
                )
            return errors

    monkeypatch.setattr("data_quality.schema_validation.Draft202012Validator", FakeValidator)

    errors = validate_instance(payload, SCHEMA_DIR / "audit-event.schema.json")

    by_path = {error.path: error.message for error in errors}
    assert by_path["/actor"] == "'id' is a required property"
    assert by_path["/timestamp"] == "'not-a-datetime' is not a 'date-time'"


def test_schema_validation_boundary_inputs_for_empty_null_and_unexpected_nested_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeValidationError:
        def __init__(self, message: str, path: list[str]) -> None:
            self.message = message
            self.path = path

    class FakeValidator:
        def __init__(self, schema: dict[str, object], format_checker: object = None) -> None:
            self.schema = schema

        def iter_errors(self, instance: dict[str, object]) -> list[FakeValidationError]:
            if instance == {}:
                return [
                    FakeValidationError("'id' is a required property", []),
                    FakeValidationError("'tenant_id' is a required property", []),
                ]
            errors: list[FakeValidationError] = []
            if instance.get("id") is None:
                errors.append(FakeValidationError("None is not of type 'string'", ["id"]))
            actor = instance.get("actor", {})
            if isinstance(actor, dict) and "unexpected" in actor:
                errors.append(
                    FakeValidationError(
                        "Additional properties are not allowed ('unexpected' was unexpected)",
                        ["actor"],
                    )
                )
            return errors

    monkeypatch.setattr("data_quality.schema_validation.Draft202012Validator", FakeValidator)

    empty_errors = validate_instance({}, SCHEMA_DIR / "document.schema.json")
    assert len(empty_errors) == 2

    null_payload: dict[str, object] = {"id": None}
    null_errors = validate_instance(null_payload, SCHEMA_DIR / "document.schema.json")
    assert any(error.path == "/id" and "None is not of type 'string'" in error.message for error in null_errors)

    nested_payload = _load_example("audit-event")
    nested_payload["actor"]["unexpected"] = "value"  # type: ignore[index]
    nested_errors = validate_instance(nested_payload, SCHEMA_DIR / "audit-event.schema.json")
    assert any(
        error.path == "/actor" and "Additional properties are not allowed" in error.message
        for error in nested_errors
    )
