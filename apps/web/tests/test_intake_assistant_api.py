import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

pytest.importorskip("email_validator")

import main  # noqa: E402


def test_intake_assistant_returns_questions_and_proposals_for_business_step():
    client = TestClient(main.app)
    response = client.post(
        "/v1/api/intake/assistant",
        json={
            "step_id": "business",
            "step_index": 1,
            "form_state": {
                "businessSummary": "",
                "businessJustification": "",
                "expectedBenefits": "",
            },
            "validation_errors": {"expectedBenefits": "Expected benefits are required."},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["step_id"] == "business"
    assert "expectedBenefits" in payload["proposals"]
    assert payload["questions"]
    assert any("Validation issue" in question for question in payload["questions"])


def test_intake_assistant_adds_confirmation_hint_for_non_empty_field():
    client = TestClient(main.app)
    response = client.post(
        "/v1/api/intake/assistant",
        json={
            "step_id": "success",
            "step_index": 2,
            "form_state": {
                "successMetrics": "Already filled",
                "riskNotes": "",
            },
            "validation_errors": {},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "riskNotes" in payload["proposals"]
    assert any("safe to apply directly" in hint for hint in payload["apply_hints"])
