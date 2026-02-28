from __future__ import annotations

import logging

from connectors.clarity.src.mappers import map_to_clarity


def test_map_to_clarity_happy_path() -> None:
    records = [
        {
            "id": "clarity-100",
            "program_id": "portfolio-01",
            "name": "Core Platform Upgrade",
            "status": "approved",
            "start_date": "2024-03-01",
            "end_date": "2024-12-31",
            "owner": "delivery-lead",
            "classification": "strategic",
            "created_at": "2024-01-20T01:02:03Z",
            "tenant_id": "tenant-123",
            "source": "project",
        }
    ]

    assert map_to_clarity(records) == [
        {
            "externalId": "clarity-100",
            "programId": "portfolio-01",
            "name": "Core Platform Upgrade",
            "status": "APPROVED",
            "startDate": "2024-03-01",
            "finishDate": "2024-12-31",
            "ownerId": "delivery-lead",
            "classification": "strategic",
            "createdDate": "2024-01-20T01:02:03Z",
            "sourceSystem": "canonical-ppm",
            "metadata": {"tenantId": "tenant-123", "source": "project"},
        }
    ]


def test_map_to_clarity_missing_optional_fields() -> None:
    records = [
        {
            "id": "clarity-101",
            "title": "Fallback title",
            "status": "execution",
            "start_date": "2024-04-01",
            "end_date": "2024-05-01",
            "owner_id": "pm-1",
        }
    ]

    assert map_to_clarity(records) == [
        {
            "externalId": "clarity-101",
            "name": "Fallback title",
            "status": "IN_PROGRESS",
            "startDate": "2024-04-01",
            "finishDate": "2024-05-01",
            "ownerId": "pm-1",
            "sourceSystem": "canonical-ppm",
        }
    ]


def test_map_to_clarity_invalid_values_are_skipped(caplog) -> None:
    caplog.set_level(logging.WARNING)
    records = [
        {
            "id": "clarity-102",
            "name": "Bad status",
            "status": "mystery",
            "start_date": "2024-04-01",
            "end_date": "2024-05-01",
            "owner": "pm-2",
        }
    ]

    assert map_to_clarity(records) == []
    assert "Skipping malformed Clarity outbound record" in caplog.text


def test_map_to_clarity_mixed_batch_filters_invalid_records() -> None:
    records = [
        {
            "id": "clarity-200",
            "name": "Valid",
            "status": "completed",
            "start_date": "2024-01-01",
            "end_date": "2024-01-10",
            "owner": "pm-3",
        },
        {
            "id": "clarity-201",
            "name": "Invalid date order",
            "status": "completed",
            "start_date": "2024-02-15",
            "end_date": "2024-02-01",
            "owner": "pm-4",
        },
        {
            "id": "clarity-202",
            "name": "Valid two",
            "status": "on_hold",
            "start_date": "2024-03-01",
            "end_date": "2024-03-20",
            "owner": "pm-5",
        },
    ]

    mapped = map_to_clarity(records)

    assert [payload["externalId"] for payload in mapped] == ["clarity-200", "clarity-202"]
    assert mapped[0]["status"] == "COMPLETED"
    assert mapped[1]["status"] == "ON_HOLD"
