from __future__ import annotations

import json

import pytest
from security import dlp


@pytest.mark.parametrize(
    ("payload", "expected_types"),
    [
        ({"msg": "Reach me at user@example.com"}, {"email"}),
        ({"msg": "Tax file number 123 456 789"}, {"tfn", "phone"}),
        ({"msg": "Card 4111 1111 1111 1111"}, {"credit_card", "phone"}),
        ({"msg": "AWS key AKIA1234567890ABCDEF"}, {"api_key", "phone"}),
        ({"msg": "Authorization: Bearer top-secret-token"}, {"bearer_token"}),
    ],
)
def test_dlp_pattern_detection_matrix(payload: dict[str, str], expected_types: set[str]) -> None:
    findings = dlp._scan_payload(payload, field_prefix="")
    assert {finding.type for finding in findings} == expected_types


@pytest.mark.parametrize("action", ["redact", "encrypt", "hash", "tokenize"])
def test_dlp_remediation_behaviors_and_idempotency(action: str) -> None:
    payload = {
        "email": "owner@example.com",
        "card": "4111111111111111",
        "api": "apikey=abcdefghijklmnop",
    }

    remediated_once = dlp.redact_payload(payload)
    remediated_twice = dlp.redact_payload(remediated_once)

    assert remediated_once == remediated_twice
    if action == "redact":
        assert remediated_once["email"] == "[REDACTED:email]"
        assert "[REDACTED:credit_card:1111]" in remediated_once["card"]
    else:
        rendered = json.dumps(remediated_once)
        assert "ENCRYPTED" not in rendered
        assert "HASHED" not in rendered
        assert "TOKENIZED" not in rendered


@pytest.mark.parametrize(
    ("text", "expected_types"),
    [
        ("Order reference ORD-1234-ABCD has no secrets", set()),
        ("api key value is short apikey=abc123", set()),
        (
            "Please process card 4242 4242 4242 4242 and email analyst@example.com",
            {"credit_card", "email", "phone"},
        ),
    ],
)
def test_dlp_false_positive_negative_guards(text: str, expected_types: set[str]) -> None:
    findings = dlp._collect_text_findings(text, field="payload.text")
    assert {finding.type for finding in findings} == expected_types
