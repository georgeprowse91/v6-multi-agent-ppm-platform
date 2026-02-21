from __future__ import annotations

from datetime import date, timedelta

from ops.tools.check_connector_maturity import _evaluate


def _inventory() -> dict:
    return {
        "connectors": [
            {
                "id": "jira",
                "business_priority": 1,
                "coverage": {
                    "read": True,
                    "write": False,
                    "webhook": True,
                    "mapping_completeness": 1.0,
                },
            },
            {
                "id": "workday",
                "business_priority": 5,
                "coverage": {
                    "read": True,
                    "write": True,
                    "webhook": True,
                    "mapping_completeness": 0.5,
                },
            },
        ],
        "gaps": {"incomplete_mapping": ["workday"]},
    }


def _policy() -> dict:
    return {
        "thresholds": {
            "mappings": {"rule_id": "missing_manifest_mappings", "max_missing_connectors": 0},
            "tier1": {
                "max_business_priority": 5,
                "required_capabilities": ["read", "write", "webhook"],
            },
        },
        "exceptions": [],
    }


def test_evaluate_reports_mapping_and_tier1_violations() -> None:
    violations, exception_violations = _evaluate(_policy(), _inventory())

    rule_ids = {violation.rule_id for violation in violations}
    assert "tier1_required_capabilities" in rule_ids
    assert "missing_manifest_mappings" in rule_ids
    assert not exception_violations


def test_evaluate_honors_unexpired_exceptions() -> None:
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    policy = _policy()
    policy["exceptions"] = [
        {
            "connector_id": "workday",
            "rule_id": "missing_manifest_mappings",
            "expires_on": tomorrow,
            "reason": "temporary rollout",
        },
        {
            "connector_id": "jira",
            "rule_id": "tier1_required_capabilities",
            "expires_on": tomorrow,
            "reason": "webhook migration",
        },
    ]

    violations, exception_violations = _evaluate(policy, _inventory())

    assert not exception_violations
    assert not violations


def test_evaluate_flags_expired_exceptions() -> None:
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    policy = _policy()
    policy["exceptions"] = [
        {
            "connector_id": "jira",
            "rule_id": "tier1_required_capabilities",
            "expires_on": yesterday,
            "reason": "should fail",
        }
    ]

    _, exception_violations = _evaluate(policy, _inventory())

    assert any(violation.rule_id == "expired_exception" for violation in exception_violations)
