from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = SERVICE_ROOT / "src"
MODULE_PATH = SRC_ROOT / "main.py"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

spec = spec_from_file_location("agent_runtime_main", MODULE_PATH)
assert spec and spec.loader
module = module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

client = TestClient(module.app)


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "agent-runtime"


def test_list_agents_includes_catalog() -> None:
    response = client.get("/agents")
    assert response.status_code == 200
    payload = response.json()
    agent_ids = {agent["agent_id"] for agent in payload}
    assert "intent-router" in agent_ids
    assert "response-orchestration" in agent_ids
    assert len(agent_ids) == 25


def test_intent_router_routes_demand_intake() -> None:
    response = client.post(
        "/agents/intent-router/execute",
        json={"payload": {"query": "Submit a demand intake request for a new project idea"}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    routing = payload["data"]["routing"]
    assert any(route["agent_id"] == "demand-intake" for route in routing)


def test_orchestration_config_drives_execution() -> None:
    config_response = client.put(
        "/orchestration/config",
        json={
            "default_routing": [
                {"agent_id": "demand-intake", "action": "get_pipeline", "depends_on": []}
            ],
            "last_updated_by": "tests",
        },
    )
    assert config_response.status_code == 200

    response = client.post(
        "/orchestration/run",
        json={"parameters": {}, "context": {"tenant_id": "test-tenant"}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["agent_results"][0]["success"] is True


def test_connector_action_is_returned() -> None:
    response = client.post(
        "/agents/demand-intake/execute",
        json={
            "payload": {
                "action": "get_pipeline",
                "connector_actions": [
                    {
                        "connector_id": "jira",
                        "action": "create_issue",
                        "payload": {"summary": "Escalate demand intake"},
                    }
                ],
            }
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    connector_results = payload["data"]["connector_results"]
    assert connector_results[0]["connector_id"] == "jira"


def test_approval_workflow_escalation_metadata() -> None:
    response = client.post(
        "/agents/agent_003_approval_workflow/execute",
        json={
            "payload": {
                "request_type": "budget_change",
                "request_id": "REQ-100",
                "requester": "user-1",
                "details": {"amount": 25000, "description": "Expand scope", "urgency": "high"},
            }
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["metadata"]["escalation_scheduled"] is True
