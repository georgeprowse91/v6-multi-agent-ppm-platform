from __future__ import annotations

import importlib
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

WORKFLOW_PACKAGE = Path(__file__).resolve().parents[2] / "packages" / "workflow" / "src"
if str(WORKFLOW_PACKAGE) not in sys.path:
    sys.path.insert(0, str(WORKFLOW_PACKAGE))

pytest.importorskip("cryptography")


def _load_module():
    module_path = (
        Path(__file__).resolve().parents[2] / "apps" / "workflow-service" / "src" / "main.py"
    )
    spec = spec_from_file_location("workflow_service_main", module_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class DummyAgentClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    async def execute(self, agent_id: str, action: str, payload: dict, context: dict) -> dict:
        self.calls.append({"agent_id": agent_id, "action": action})
        return {"status": "ok"}


def test_workflow_persistence(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "workflow.db"
    monkeypatch.setenv("WORKFLOW_DB_PATH", str(db_path))
    monkeypatch.setenv("WORKFLOW_CELERY_EAGER", "true")
    monkeypatch.setenv("WORKFLOW_BROKER_URL", "memory://")
    monkeypatch.setenv("WORKFLOW_RESULT_BACKEND", "cache+memory://")
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    monkeypatch.setenv("AGENT_SERVICE_URL", "http://agent.test")

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
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"}

    module = _load_module()
    workflow_tasks = importlib.import_module("workflow.tasks")
    # Reset the cached context so the task creates a fresh store pointing to
    # this test's db_path (a stale context from a previous test would use an
    # old, now-deleted, temp database).
    workflow_tasks._CONTEXT = None
    workflow_tasks.AGENT_CLIENT_OVERRIDE = DummyAgentClient()
    client = TestClient(module.app)

    response = client.post(
        "/v1/workflows/start",
        json={
            "workflow_id": "intake-triage",
            "tenant_id": "tenant-alpha",
            "classification": "internal",
            "payload": {"request": "run"},
            "actor": {"id": "user-123", "type": "user", "roles": ["portfolio_admin"]},
        },
        headers=headers,
    )
    assert response.status_code == 200
    run_id = response.json()["run_id"]
    assert workflow_tasks.AGENT_CLIENT_OVERRIDE.calls

    fetch = client.get(f"/v1/workflows/{run_id}", headers=headers)
    assert fetch.status_code == 200
    assert fetch.json()["run_id"] == run_id


def test_compensation_recovery_endpoints(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "workflow.db"
    monkeypatch.setenv("WORKFLOW_DB_PATH", str(db_path))
    monkeypatch.setenv("WORKFLOW_CELERY_EAGER", "true")
    monkeypatch.setenv("WORKFLOW_BROKER_URL", "memory://")
    monkeypatch.setenv("WORKFLOW_RESULT_BACKEND", "cache+memory://")
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    monkeypatch.setenv("AGENT_SERVICE_URL", "http://agent.test")

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
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"}

    module = _load_module()
    module.runtime.agent_client = DummyAgentClient()
    definition = {
        "metadata": {"name": "Comp", "version": "v1", "owner": "qa"},
        "steps": [
            {
                "id": "step-a",
                "type": "task",
                "next": None,
                "config": {"agent": "agent-a", "action": "run"},
                "compensation": {"agent": "agent-a", "action": "undo"},
            }
        ],
    }
    module.store.upsert_definition("comp-endpoint", definition)
    run = module.store.create(
        "run-endpoint", "comp-endpoint", "tenant-alpha", {"payload": True}, current_step_id="step-a"
    )
    module.store.add_journal_entry(
        run.run_id,
        phase="execution",
        status="completed",
        attempt=1,
        step_id="step-a",
        details={"compensable": True},
    )
    module.store.update_status(run.run_id, "compensation_failed", "step-a")

    client = TestClient(module.app)

    journal = client.get(f"/v1/workflows/{run.run_id}/compensation", headers=headers)
    assert journal.status_code == 200
    assert journal.json() == []

    retry = client.post(
        f"/v1/workflows/{run.run_id}/compensation/retry",
        json={"step_id": "step-a"},
        headers=headers,
    )
    assert retry.status_code == 200
    assert retry.json()["status"] == "failed"

    journal_after = client.get(f"/v1/workflows/{run.run_id}/compensation", headers=headers)
    assert journal_after.status_code == 200
    assert any(entry["status"] == "completed" for entry in journal_after.json())
