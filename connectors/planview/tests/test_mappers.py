from __future__ import annotations

import pytest

from connectors.planview.src.mappers import PlanviewMappingError, map_to_planview


def test_map_to_planview_happy_path_with_financials() -> None:
    payload = map_to_planview(
        [
            {
                "id": "proj-1",
                "program_id": "prog-9",
                "name": "Migration",
                "status": "execution",
                "start_date": "2024-01-01",
                "end_date": "2024-03-01",
                "owner": "owner@example.com",
                "classification": "internal",
                "planned_cost": "1000.5",
                "actual_cost": 500,
                "currency": "eur",
                "created_at": "2024-01-01T01:02:03Z",
                "updated_at": "2024-02-01T03:04:05Z",
                "tenant_id": "tenant-1",
            }
        ]
    )

    assert payload == [
        {
            "externalId": "proj-1",
            "name": "Migration",
            "lifecycleState": "active",
            "startDate": "2024-01-01",
            "finishDate": "2024-03-01",
            "parentProgramExternalId": "prog-9",
            "owner": {"principalName": "owner@example.com"},
            "financials": {
                "classification": "INTERNAL",
                "plannedCost": 1000.5,
                "actualCost": 500.0,
                "currency": "eur",
            },
            "metadata": {
                "sourceCreatedAt": "2024-01-01T01:02:03Z",
                "sourceUpdatedAt": "2024-02-01T03:04:05Z",
                "sourceTenantId": "tenant-1",
            },
        }
    ]


def test_map_to_planview_batch_failure_includes_context() -> None:
    records = [
        {
            "id": "good-1",
            "name": "Good",
            "status": "open",
            "start_date": "2024-01-01",
        },
        {
            "id": "bad-2",
            "name": "Bad",
            "status": "unknown-status",
            "start_date": "2024-01-01",
        },
    ]

    with pytest.raises(PlanviewMappingError) as exc_info:
        map_to_planview(records)

    error = exc_info.value
    assert error.index == 1
    assert error.field == "status"
    assert error.record_id == "bad-2"


def test_map_to_planview_requires_fields_and_valid_dates() -> None:
    with pytest.raises(PlanviewMappingError, match="Missing required field: name"):
        map_to_planview([{"id": "x", "status": "open", "start_date": "2024-01-01"}])

    with pytest.raises(PlanviewMappingError, match="Invalid date format for start_date"):
        map_to_planview(
            [{"id": "x", "name": "Name", "status": "open", "start_date": "01/01/2024"}]
        )

    with pytest.raises(PlanviewMappingError, match="Invalid numeric value for planned_cost"):
        map_to_planview(
            [
                {
                    "id": "x",
                    "name": "Name",
                    "status": "open",
                    "start_date": "2024-01-01",
                    "planned_cost": "not-a-number",
                }
            ]
        )
