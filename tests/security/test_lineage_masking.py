from __future__ import annotations

import json

from security.lineage import mask_lineage_payload


def test_lineage_masking_removes_pii(monkeypatch) -> None:
    monkeypatch.setenv("LINEAGE_MASK_SALT", "unit-test-salt")
    lineage_payload = {
        "dataset": "portfolio_summary",
        "actor": {"email": "jane.doe@example.com", "full_name": "Jane Doe"},
        "records": [
            {
                "source": "hr_system",
                "email": "jane.doe@example.com",
                "phone": "+1 (555) 555-0101",
                "ssn": "123-45-6789",
            }
        ],
    }

    masked = mask_lineage_payload(lineage_payload)
    payload_json = json.dumps(masked)

    assert "jane.doe@example.com" not in payload_json
    assert "123-45-6789" not in payload_json
    assert "+1 (555) 555-0101" not in payload_json
    assert masked["dataset"] == "portfolio_summary"
    assert masked["actor"]["email"].startswith("masked_")
    assert masked["actor"]["full_name"].startswith("masked_")


def test_lineage_masking_is_deterministic(monkeypatch) -> None:
    monkeypatch.setenv("LINEAGE_MASK_SALT", "unit-test-salt")
    lineage_payload = {"email": "john.smith@example.com"}

    first = mask_lineage_payload(lineage_payload)
    second = mask_lineage_payload(lineage_payload)

    assert first["email"] == second["email"]
