from __future__ import annotations

from datetime import date, datetime

import pytest

from integrations.connectors.sap.src.mappers import map_to_sap


def test_map_to_sap_has_expected_shape() -> None:
    payload = map_to_sap(
        [
            {
                "id": "P-100",
                "name": "ERP rollout",
                "status": "active",
                "start_date": "2024-01-05",
                "end_date": "2024-06-10",
                "owner": "manager-a",
            }
        ]
    )

    assert payload == [
        {
            "ProjectID": "P-100",
            "Description": "ERP rollout",
            "LifecycleStatus": "REL",
            "PlannedStartDate": "2024-01-05",
            "PlannedFinishDate": "2024-06-10",
            "ProjectManager": "manager-a",
            "BudgetAmount": None,
            "PercentComplete": None,
            "IsActive": True,
        }
    ]


def test_map_to_sap_missing_required_data_raises() -> None:
    with pytest.raises(ValueError, match="missing required fields: name"):
        map_to_sap(
            [
                {
                    "id": "P-100",
                    "name": "",
                    "status": "active",
                    "start_date": "2024-01-05",
                    "end_date": "2024-06-10",
                }
            ]
        )


def test_map_to_sap_converts_types_and_formats() -> None:
    payload = map_to_sap(
        [
            {
                "id": 200,
                "name": "Project 200",
                "status": "completed",
                "start_date": datetime(2024, 1, 5, 13, 0, 0),
                "end_date": date(2024, 6, 10),
                "budget": "12345.50",
                "progress": "87.9",
                "is_active": "false",
            }
        ]
    )

    assert payload[0]["ProjectID"] == "200"
    assert payload[0]["LifecycleStatus"] == "CMP"
    assert payload[0]["PlannedStartDate"] == "2024-01-05"
    assert payload[0]["PlannedFinishDate"] == "2024-06-10"
    assert payload[0]["BudgetAmount"] == 12345.5
    assert payload[0]["PercentComplete"] == 87
    assert payload[0]["IsActive"] is False


def test_map_to_sap_supports_multi_record_batches() -> None:
    payload = map_to_sap(
        [
            {
                "id": "P-1",
                "name": "One",
                "status": "planned",
                "start_date": "2024-01-01",
                "end_date": "2024-02-01",
            },
            {
                "id": "P-2",
                "name": "Two",
                "status": "cancelled",
                "start_date": "2024-03-01",
                "end_date": "2024-04-01",
            },
        ]
    )

    assert [item["ProjectID"] for item in payload] == ["P-1", "P-2"]
    assert [item["LifecycleStatus"] for item in payload] == ["PLN", "CNL"]
