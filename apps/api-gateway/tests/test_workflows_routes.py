from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api.routes import workflows


@pytest.mark.anyio
async def test_create_definition_happy_path(monkeypatch):
    record = SimpleNamespace(
        workflow_id="demo",
        name="Demo Workflow",
        version="1.0.0",
        owner="platform",
        description="test",
    )
    monkeypatch.setattr(workflows.store, "upsert_definition", lambda *_args, **_kwargs: record, raising=False)

    response = await workflows.create_definition(
        workflows.WorkflowDefinitionCreateRequest(workflow_id="demo", definition={"name": "Demo"})
    )

    assert response.workflow_id == "demo"
    assert response.name == "Demo Workflow"


@pytest.mark.anyio
async def test_start_workflow_raises_when_runtime_fails(monkeypatch):
    instance = SimpleNamespace(
        run_id="run-1",
        workflow_id="demo",
        tenant_id="tenant-a",
        status="pending",
        current_step_id=None,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
    )

    async def _boom(*_args, **_kwargs):
        raise RuntimeError("internal execution failure")

    runtime = SimpleNamespace(start=_boom)
    monkeypatch.setattr(workflows, "_get_definition", lambda _workflow_id: {"workflow_id": "demo"})
    monkeypatch.setattr(workflows.store, "create", lambda *_args, **_kwargs: instance, raising=False)
    monkeypatch.setattr(workflows, "_get_runtime", lambda _request: runtime)
    
    async def _no_approval(**_kwargs):
        return None

    monkeypatch.setattr(workflows, "_route_change_approval", _no_approval)

    http_request = SimpleNamespace(state=SimpleNamespace(auth=SimpleNamespace(tenant_id="tenant-a")))
    request = workflows.WorkflowStartRequest(
        workflow_id="demo",
        payload={"x": 1},
        actor={"id": "user-1"},
    )

    with pytest.raises(RuntimeError):
        await workflows.start_workflow(request, http_request)


@pytest.mark.anyio
async def test_get_instance_missing_workflow_returns_404(monkeypatch):
    monkeypatch.setattr(workflows.store, "get", lambda _run_id: None, raising=False)

    request = SimpleNamespace(state=SimpleNamespace(auth=SimpleNamespace(tenant_id="tenant-a")))
    with pytest.raises(HTTPException) as exc_info:
        await workflows.get_instance("missing-run", request)

    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_get_instance_tenant_mismatch_returns_403(monkeypatch):
    instance = SimpleNamespace(
        run_id="run-1",
        workflow_id="demo",
        tenant_id="tenant-a",
        status="running",
        current_step_id="step-1",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
    )
    monkeypatch.setattr(workflows.store, "get", lambda _run_id: instance, raising=False)

    request = SimpleNamespace(state=SimpleNamespace(auth=SimpleNamespace(tenant_id="tenant-b")))
    with pytest.raises(HTTPException) as exc_info:
        await workflows.get_instance("run-1", request)

    assert exc_info.value.status_code == 403


def test_get_definition_invalid_definition_maps_to_422(monkeypatch, tmp_path):
    monkeypatch.setattr(workflows.store, "get_definition", lambda _workflow_id: None, raising=False)
    monkeypatch.setattr(workflows, "DEFINITIONS_DIR", tmp_path)
    workflow_file = tmp_path / "broken.workflow.yaml"
    workflow_file.write_text("invalid: true", encoding="utf-8")

    def _raise_value_error(*_args, **_kwargs):
        raise ValueError("schema invalid")

    monkeypatch.setattr(workflows, "load_definition", _raise_value_error)

    with pytest.raises(HTTPException) as exc_info:
        workflows._get_definition("broken")

    assert exc_info.value.status_code == 422
