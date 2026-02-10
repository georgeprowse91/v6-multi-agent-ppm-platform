from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY_MODULE = ROOT / "agents" / "runtime" / "src" / "policy.py"
AUDIT_MODULE = ROOT / "agents" / "runtime" / "src" / "audit.py"

policy_spec = importlib.util.spec_from_file_location("runtime_policy", POLICY_MODULE)
audit_spec = importlib.util.spec_from_file_location("runtime_audit", AUDIT_MODULE)
assert policy_spec and policy_spec.loader and audit_spec and audit_spec.loader
policy_module = importlib.util.module_from_spec(policy_spec)
audit_module = importlib.util.module_from_spec(audit_spec)
sys.modules[policy_spec.name] = policy_module
sys.modules[audit_spec.name] = audit_module
policy_spec.loader.exec_module(policy_module)
audit_spec.loader.exec_module(audit_module)


def test_data_without_consent_is_rejected() -> None:
    decision = policy_module.evaluate_compliance_controls(
        {
            "personal_data": {"email": "user@example.com", "medical_record": "MRN-123"},
            "consent": {"granted": False},
        }
    )

    assert decision.decision == "deny"
    assert "consent_missing" in decision.reasons


def test_sensitive_fields_are_masked_or_removed() -> None:
    decision = policy_module.evaluate_compliance_controls(
        {
            "personal_data": {
                "email": "user@example.com",
                "phone": "+1-555-1234",
                "favorite_color": "blue",
                "medical_record": "MRN-123",
            },
            "consent": {"granted": True},
        }
    )

    sanitized = decision.sanitized_payload["personal_data"]
    assert decision.decision == "allow"
    assert sanitized["email"] != "user@example.com"
    assert sanitized["phone"] != "+1-555-1234"
    assert "favorite_color" not in sanitized
    assert "medical_record" in sanitized
    assert "data_minimization_removed:favorite_color" in decision.reasons


def test_audit_event_contains_compliance_metadata() -> None:
    event = audit_module.build_audit_event(
        tenant_id="tenant-alpha",
        action="compliance.data.access",
        outcome="success",
        actor_id="agent-016",
        actor_type="service",
        actor_roles=["compliance"],
        resource_id="project-1",
        resource_type="project",
        legal_basis="consent",
        retention_period="P3Y",
    )

    assert event["legal_basis"] == "consent"
    assert event["retention_period"] == "P3Y"
