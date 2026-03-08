"""Tests for security posture endpoints (Enhancement 9).

Tests cover posture scoring, policy evaluation with real condition engine,
classification tracking, and policy CRUD.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import router directly to avoid routes/__init__.py triggering unrelated imports.
_mod_path = (
    Path(__file__).resolve().parents[2] / "apps" / "web" / "src" / "routes" / "security_posture.py"
)
_spec = importlib.util.spec_from_file_location("security_posture", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["security_posture"] = _mod
_spec.loader.exec_module(_mod)
_router = _mod.router


def _make_app():
    app = FastAPI()
    app.include_router(_router)
    return app


@pytest.fixture
def client():
    return TestClient(_make_app())


def test_security_posture(client):
    resp = client.get("/api/security/posture")
    assert resp.status_code == 200
    data = resp.json()
    assert "posture_score" in data
    assert 0 <= data["posture_score"] <= 100
    assert "compliance_checks" in data
    assert data["policy_count"] > 0


def test_list_policies(client):
    resp = client.get("/api/security/policies")
    assert resp.status_code == 200
    policies = resp.json()
    assert len(policies) > 0
    assert all("policy_id" in p for p in policies)


def test_test_policy_deny(client):
    resp = client.post(
        "/api/security/policies/test",
        json={
            "policy": {
                "policy_id": "test-pol",
                "name": "Test",
                "description": "test",
                "effect": "deny",
                "subjects": {},
                "resources": {},
                "actions": ["read"],
                "conditions": [{"field": "subject.role", "operator": "equals", "value": "admin"}],
                "enabled": True,
            },
            "context": {"subject": {"role": "admin"}},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "deny"


def test_test_policy_allow_when_no_match(client):
    """Policy with conditions that don't match should allow."""
    resp = client.post(
        "/api/security/policies/test",
        json={
            "policy": {
                "policy_id": "test-pol-2",
                "name": "Test2",
                "description": "test",
                "effect": "deny",
                "subjects": {},
                "resources": {},
                "actions": ["read"],
                "conditions": [{"field": "subject.role", "operator": "equals", "value": "admin"}],
                "enabled": True,
            },
            "context": {"subject": {"role": "viewer"}},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "allow"


def test_test_policy_not_between(client):
    """Test the not_between operator for time-based policies."""
    resp = client.post(
        "/api/security/policies/test",
        json={
            "policy": {
                "policy_id": "test-time",
                "name": "Time Policy",
                "description": "test",
                "effect": "deny",
                "conditions": [
                    {"field": "request.hour", "operator": "not_between", "value": [8, 18]}
                ],
            },
            "context": {"request": {"hour": 22}},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "deny"


def test_classification_stats(client):
    resp = client.get("/api/security/classification-stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "public" in data
    assert "restricted" in data


def test_classify_entity(client):
    resp = client.post(
        "/api/security/classify-entity",
        json={"entity_type": "project", "entity_id": "proj-001", "classification": "confidential"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "applied"

    # Verify it shows up in stats
    stats = client.get("/api/security/classification-stats").json()
    assert stats["confidential"] >= 1


# --- Error path and edge case tests ---


def test_test_policy_unconditional_deny(client):
    """Policy with no conditions that exists should apply its effect unconditionally."""
    # First create the policy
    client.post(
        "/api/security/policies",
        json={
            "policy_id": "test-uncon",
            "name": "Unconditional Deny",
            "description": "always deny",
            "effect": "deny",
            "conditions": [],
        },
    )
    resp = client.post(
        "/api/security/policies/test",
        json={
            "policy": {
                "policy_id": "test-uncon",
                "name": "Unconditional Deny",
                "description": "always deny",
                "effect": "deny",
                "conditions": [],
            },
            "context": {},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "deny"


def test_test_policy_unknown_unconditional_returns_404(client):
    """Testing a nonexistent unconditional policy should return 404."""
    resp = client.post(
        "/api/security/policies/test",
        json={
            "policy": {
                "policy_id": "not-registered",
                "name": "Unknown",
                "description": "test",
                "effect": "deny",
                "conditions": [],
            },
            "context": {},
        },
    )
    assert resp.status_code == 404


def test_test_policy_gt_operator(client):
    """Test the gt (greater than) operator."""
    resp = client.post(
        "/api/security/policies/test",
        json={
            "policy": {
                "policy_id": "test-gt",
                "name": "GT Test",
                "description": "test",
                "effect": "deny",
                "conditions": [{"field": "request.amount", "operator": "gt", "value": 1000}],
            },
            "context": {"request": {"amount": 1500}},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "deny"


def test_test_policy_gt_not_matched(client):
    """GT condition should not match when value is lower."""
    resp = client.post(
        "/api/security/policies/test",
        json={
            "policy": {
                "policy_id": "test-gt-low",
                "name": "GT Low",
                "description": "test",
                "effect": "deny",
                "conditions": [{"field": "request.amount", "operator": "gt", "value": 1000}],
            },
            "context": {"request": {"amount": 500}},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "allow"


def test_test_policy_not_in_operator(client):
    """Test the not_in operator."""
    resp = client.post(
        "/api/security/policies/test",
        json={
            "policy": {
                "policy_id": "test-notin",
                "name": "Not In Test",
                "description": "test",
                "effect": "deny",
                "conditions": [
                    {"field": "subject.region", "operator": "not_in", "value": ["US", "EU"]}
                ],
            },
            "context": {"subject": {"region": "CN"}},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "deny"


def test_test_policy_contains_operator(client):
    """Test the contains operator."""
    resp = client.post(
        "/api/security/policies/test",
        json={
            "policy": {
                "policy_id": "test-contains",
                "name": "Contains Test",
                "description": "test",
                "effect": "deny",
                "conditions": [
                    {"field": "subject.groups", "operator": "contains", "value": "admin"}
                ],
            },
            "context": {"subject": {"groups": "admin,user,viewer"}},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "deny"


def test_posture_score_range(client):
    """Posture score should always be between 0 and 100."""
    resp = client.get("/api/security/posture")
    data = resp.json()
    assert 0 <= data["posture_score"] <= 100
    assert 0 <= data["abac_coverage_pct"] <= 100


def test_create_policy(client):
    """Creating a new policy should succeed."""
    resp = client.post(
        "/api/security/policies",
        json={
            "policy_id": "new-pol",
            "name": "New Policy",
            "description": "A new test policy",
            "effect": "deny",
            "conditions": [],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["policy_id"] == "new-pol"


def test_update_existing_policy(client):
    """Updating an existing policy should replace it."""
    client.post(
        "/api/security/policies",
        json={
            "policy_id": "upd-pol",
            "name": "V1",
            "description": "v1",
            "effect": "deny",
            "conditions": [],
        },
    )
    resp = client.post(
        "/api/security/policies",
        json={
            "policy_id": "upd-pol",
            "name": "V2",
            "description": "v2",
            "effect": "allow",
            "conditions": [],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "V2"


def test_classify_multiple_entities(client):
    """Multiple entities can be classified independently."""
    for i in range(3):
        client.post(
            "/api/security/classify-entity",
            json={"entity_type": "document", "entity_id": f"doc-{i}", "classification": "internal"},
        )
    stats = client.get("/api/security/classification-stats").json()
    assert stats["internal"] >= 3


def test_compliance_checks_present(client):
    """Posture should include compliance check frameworks."""
    resp = client.get("/api/security/posture")
    checks = resp.json()["compliance_checks"]
    frameworks = {c["framework"] for c in checks}
    assert "SOC 2" in frameworks
    assert "GDPR" in frameworks
