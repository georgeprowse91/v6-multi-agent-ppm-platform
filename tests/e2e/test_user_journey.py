from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
from fastapi.testclient import TestClient


_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_app(path: Path, module_name: str, extra_src: Path | None = None):
    # Prepend the app's own src directory so its config.py takes priority over
    # any other config.py that may be earlier in sys.path (e.g. apps/web/src).
    src_dir = str(path.parent.resolve())

    # Snapshot state to restore after loading so we don't pollute other tests.
    original_path = sys.path[:]
    original_config = sys.modules.get("config")

    try:
        # Temporarily move the app src to position 0 for correct config.py resolution.
        if src_dir in sys.path:
            sys.path.remove(src_dir)
        sys.path.insert(0, src_dir)
        if extra_src:
            extra = str(extra_src.resolve())
            if extra in sys.path:
                sys.path.remove(extra)
            sys.path.insert(0, extra)
        # Clear any cached 'config' module so the correct app-specific one loads.
        for mod_name in list(sys.modules):
            if mod_name in {"config", module_name}:
                sys.modules.pop(mod_name, None)
        spec = spec_from_file_location(module_name, path)
        module = module_from_spec(spec)
        assert spec and spec.loader
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module.app
    finally:
        # Restore sys.path so we don't pollute subsequent tests.
        sys.path[:] = original_path
        # Restore the original config module (or remove the app-specific one).
        if original_config is None:
            sys.modules.pop("config", None)
        else:
            sys.modules["config"] = original_config


def _identity_client():
    path = _REPO_ROOT / "services" / "identity-access" / "src" / "main.py"
    return TestClient(_load_app(path, "identity_access_main"))


def _gateway_client():
    from api.main import app

    return TestClient(app)


def _workflow_client():
    path = _REPO_ROOT / "apps" / "workflow-service" / "src" / "main.py"
    return TestClient(_load_app(path, "workflow_service_main"))


def test_end_to_end_workflow(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    token = jwt.encode(
        {
            "sub": "user-123",
            "roles": ["portfolio_admin"],
            "aud": "ppm-platform",
            "iss": "https://issuer.example.com",
            "tenant_id": "tenant-alpha",
        },
        "test-secret",
        algorithm="HS256",
    )

    identity = _identity_client()
    identity_response = identity.post("/v1/auth/validate", json={"token": token})
    assert identity_response.status_code == 200
    assert identity_response.json()["active"] is True

    mock_orchestrator = MagicMock()
    mock_orchestrator.initialized = True
    mock_orchestrator.process_query = AsyncMock(
        return_value={
            "success": True,
            "data": {"ok": True},
            "metadata": {
                "agent_id": "intent-router-agent",
                "catalog_id": "intent-router-agent",
                "timestamp": "2024-01-01T00:00:00Z",
                "correlation_id": "test-corr-e2e",
            },
        }
    )

    gateway = _gateway_client()
    with patch("api.main.orchestrator", mock_orchestrator):
        response = gateway.post(
            "/v1/query",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"},
            json={"query": "Start workflow", "classification": "internal"},
        )
    assert response.status_code == 200

    workflow = _workflow_client()
    workflow_response = workflow.post(
        "/v1/workflows/start",
        json={
            "workflow_id": "intake-triage",
            "tenant_id": "tenant-alpha",
            "classification": "internal",
            "payload": {"request": "upgrade"},
            "actor": {"id": "user-123", "type": "user", "roles": ["portfolio_admin"]},
        },
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"},
    )
    assert workflow_response.status_code == 200
    assert workflow_response.json()["status"] == "running"


def test_workflow_resume_after_mid_workflow_failure(monkeypatch, tmp_path) -> None:
    """Simulate a failed run and verify resume continues from the same run id."""
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    monkeypatch.setenv("WORKFLOW_DB_PATH", str(tmp_path / "workflows.db"))
    token = jwt.encode(
        {
            "sub": "user-123",
            "roles": ["workflow_operator", "portfolio_admin"],
            "aud": "ppm-platform",
            "iss": "https://issuer.example.com",
            "tenant_id": "tenant-alpha",
        },
        "test-secret",
        algorithm="HS256",
    )

    workflow = _workflow_client()
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"}

    start = workflow.post(
        "/v1/workflows/start",
        json={
            "workflow_id": "intake-triage",
            "tenant_id": "tenant-alpha",
            "classification": "internal",
            "payload": {"request": "upgrade"},
            "actor": {"id": "user-123", "type": "user", "roles": ["portfolio_admin"]},
        },
        headers=headers,
    )
    assert start.status_code == 200
    run_id = start.json()["run_id"]

    fail = workflow.post(
        f"/v1/workflows/{run_id}/status", json={"status": "failed"}, headers=headers
    )
    assert fail.status_code == 200
    assert fail.json()["status"] == "failed"

    resume = workflow.post(f"/v1/workflows/{run_id}/resume", headers=headers)
    assert resume.status_code == 200
    assert resume.json()["run_id"] == run_id
    assert resume.json()["status"] == "running"


def test_workflow_idempotency_prevents_duplicate_side_effects(monkeypatch, tmp_path) -> None:
    """Repeated starts with the same idempotency key should return the same run id."""
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    monkeypatch.setenv("WORKFLOW_DB_PATH", str(tmp_path / "workflows-idempotent.db"))
    token = jwt.encode(
        {
            "sub": "user-123",
            "roles": ["workflow_operator", "portfolio_admin"],
            "aud": "ppm-platform",
            "iss": "https://issuer.example.com",
            "tenant_id": "tenant-alpha",
        },
        "test-secret",
        algorithm="HS256",
    )

    workflow = _workflow_client()
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": "tenant-alpha",
        "Idempotency-Key": "idem-key-001",
    }
    request_payload = {
        "workflow_id": "intake-triage",
        "tenant_id": "tenant-alpha",
        "classification": "internal",
        "payload": {"request": "upgrade"},
        "actor": {"id": "user-123", "type": "user", "roles": ["portfolio_admin"]},
    }

    first = workflow.post("/v1/workflows/start", json=request_payload, headers=headers)
    second = workflow.post("/v1/workflows/start", json=request_payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["run_id"] == second.json()["run_id"]


def test_workflow_service_degraded_health_when_store_unavailable(monkeypatch) -> None:
    """Workflow health endpoint should surface degraded mode when dependencies are down."""
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    workflow = _workflow_client()

    with patch("workflow_service_main.store.ping", side_effect=RuntimeError("store down")):
        health = workflow.get("/healthz")

    assert health.status_code == 503
    body = health.json()
    assert body["status"] == "degraded"
    assert body["dependencies"]["workflow_store"] == "down"
