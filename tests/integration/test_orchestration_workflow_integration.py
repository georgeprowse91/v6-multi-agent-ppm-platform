from __future__ import annotations

import importlib.util
import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import httpx
import pytest

ORCHESTRATOR_SERVICE_ROOT = (
    Path(__file__).resolve().parents[2] / "services" / "orchestration-service" / "src"
)
ORCHESTRATOR_PATH = ORCHESTRATOR_SERVICE_ROOT / "orchestrator.py"
WORKFLOW_CLIENT_PATH = ORCHESTRATOR_SERVICE_ROOT / "workflow_client.py"


def _load_module(name: str, path: Path):
    spec = spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ImportError(f"Unable to load module {name} from {path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_orchestration_service_starts_workflow_via_engine() -> None:
    try:
        spec = importlib.util.find_spec("structlog")
    except ValueError:
        # structlog is in sys.modules as a stub (set up by another test module);
        # treat it as "found" and proceed.
        spec = True
    if spec is None:
        pytest.skip("structlog is required for orchestrator module import")
    orchestrator_module = _load_module("orchestration_service_orchestrator", ORCHESTRATOR_PATH)
    workflow_module = _load_module("orchestration_service_workflow_client", WORKFLOW_CLIENT_PATH)
    AgentOrchestrator = orchestrator_module.AgentOrchestrator
    WorkflowClient = workflow_module.WorkflowClient

    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["headers"] = dict(request.headers)
        captured["json"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "run_id": "run-42",
                "workflow_id": "intake-triage",
                "tenant_id": "tenant-alpha",
                "status": "running",
                "current_step_id": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
        )

    transport = httpx.MockTransport(handler)
    workflow_client = WorkflowClient(base_url="http://workflow.test", transport=transport)
    orchestrator = AgentOrchestrator(workflow_client=workflow_client)

    response = await orchestrator.start_workflow(
        tenant_id="tenant-alpha",
        workflow_id="intake-triage",
        payload={"request": "run"},
        actor={"id": "user-1", "type": "user", "roles": ["PMO_ADMIN"]},
        headers={"Authorization": "Bearer token"},
    )

    assert response["run_id"] == "run-42"
    assert captured["method"] == "POST"
    assert captured["path"] == "/v1/workflows/start"
    assert captured["json"]["workflow_id"] == "intake-triage"
    assert captured["json"]["tenant_id"] == "tenant-alpha"
    assert captured["headers"]["x-tenant-id"] == "tenant-alpha"
