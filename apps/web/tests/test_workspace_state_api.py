import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import main  # noqa: E402
from agents.runtime.src.orchestrator import OrchestrationResult  # noqa: E402
from workspace_state_store import WorkspaceStateStore  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    main.workspace_state_store = WorkspaceStateStore(tmp_path / "workspace_state.json")
    return TestClient(main.app)


def _set_tenant(monkeypatch, tenant_id: str) -> None:
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", tenant_id)


def test_default_state_created_per_tenant(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.get("/api/workspace/demo-1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant_id"] == "tenant-a"
    assert payload["project_id"] == "demo-1"
    assert payload["current_canvas_tab"] == "document"
    assert payload["activity_completion"] == {}

    _set_tenant(monkeypatch, "tenant-b")
    response = client.get("/api/workspace/demo-1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant_id"] == "tenant-b"
    assert payload["current_canvas_tab"] == "document"


def test_select_persists_canvas_tab(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/workspace/demo-1/select",
        json={
            "current_stage_id": None,
            "current_activity_id": None,
            "current_canvas_tab": "timeline",
            "methodology": "adaptive",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["current_canvas_tab"] == "timeline"
    assert payload["methodology"] == "adaptive"

    response = client.get("/api/workspace/demo-1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["current_canvas_tab"] == "timeline"


def test_activity_completion_persists(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/workspace/demo-1/activity-completion",
        json={"activity_id": "activity-1", "completed": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["activity_completion"] == {"activity-1": True}

    response = client.get("/api/workspace/demo-1")
    payload = response.json()
    assert payload["activity_completion"]["activity-1"] is True


def test_tenant_isolation(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/workspace/demo-1/select",
        json={
            "current_stage_id": "stage-1",
            "current_activity_id": "activity-1",
            "current_canvas_tab": "tree",
            "methodology": None,
        },
    )
    assert response.status_code == 200

    _set_tenant(monkeypatch, "tenant-b")
    response = client.get("/api/workspace/demo-1")
    payload = response.json()
    assert payload["tenant_id"] == "tenant-b"
    assert payload["current_canvas_tab"] == "document"
    assert payload["current_stage_id"] is None


def test_validation_rejects_bad_tab(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/workspace/demo-1/select",
        json={
            "current_stage_id": None,
            "current_activity_id": None,
            "current_canvas_tab": "invalid",
            "methodology": None,
        },
    )
    assert response.status_code == 422

    response = client.post(
        "/api/workspace/demo-1/select",
        json={
            "current_stage_id": None,
            "current_activity_id": None,
            "current_canvas_tab": "document",
            "methodology": None,
            "tenant_id": "override",
        },
    )
    assert response.status_code == 422


def test_get_workspace_supports_methodology_query(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.get('/api/workspace/demo-1?methodology=predictive')
    assert response.status_code == 200
    payload = response.json()
    assert payload['methodology'] == 'predictive'
    assert payload['methodology_map_summary']['id'] == 'predictive'


def test_get_workspace_rejects_unknown_methodology_query(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.get('/api/workspace/demo-1?methodology=unknown')
    assert response.status_code == 422


def test_runtime_resolution_endpoints_and_workspace_enrichment(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/workspace/demo-1/select",
        json={
            "current_stage_id": "0.5-iteration-sprint-delivery-repeating-cycle",
            "current_activity_id": "0.5.1-sprint-iteration-planning",
            "current_canvas_tab": "document",
            "methodology": "adaptive",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "view" in payload["runtime_actions_available"]
    assert payload["runtime_default_view_contract"]["canvas"]["renderer_component"]

    actions = client.get(
        "/api/methodology/runtime/actions",
        params={
            "methodology_id": "adaptive",
            "stage_id": "0.5-iteration-sprint-delivery-repeating-cycle",
            "activity_id": "0.5.1-sprint-iteration-planning",
        },
    )
    assert actions.status_code == 200
    assert "generate" in actions.json()["actions"]

    resolved = client.get(
        "/api/methodology/runtime/resolve",
        params={
            "methodology_id": "adaptive",
            "stage_id": "0.5-iteration-sprint-delivery-repeating-cycle",
            "activity_id": "0.5.1-sprint-iteration-planning",
            "event": "view",
        },
    )
    assert resolved.status_code == 200
    assert resolved.json()["resolution_contract"]["assistant"]["response_contract"]["output_format"]


def test_runtime_action_endpoint_executes_orchestrator(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    captured: dict[str, object] = {}

    async def fake_run_methodology_node_action(self, **kwargs):
        captured.update(kwargs)
        return OrchestrationResult(
            results={"task-1": {"agent_id": "agent-10", "metadata": {"template_id": "adaptive-software-dev"}, "input": {}}},
            context={"correlation_id": "corr-test"},
            metrics={"templates_executed": 1},
        )

    monkeypatch.setattr(main.Orchestrator, "run_methodology_node_action", fake_run_methodology_node_action)

    response = client.post(
        "/api/methodology/runtime/action",
        json={
            "methodology_id": "adaptive",
            "stage_id": "0.5-iteration-sprint-delivery-repeating-cycle",
            "activity_id": "0.5.1-sprint-iteration-planning",
            "task_id": None,
            "lifecycle_event": "generate",
            "user_input": {"workspace_id": "demo-1"},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert captured["template_ids"] == ["adaptive-software-dev"]
    assert payload["workflow_trace"]["agent_ids_executed"] == ["agent-10"]


def test_runtime_action_known_template_mappings(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    captured: list[dict[str, object]] = []

    async def fake_run_methodology_node_action(self, **kwargs):
        captured.append(kwargs)
        template_ids = kwargs.get("template_ids", [])
        template_id = template_ids[0] if template_ids else "unknown"
        return OrchestrationResult(
            results={"task-1": {"agent_id": "agent-10", "metadata": {"template_id": template_id}, "input": {}}},
            context={"correlation_id": "corr-test"},
            metrics={"templates_executed": 1},
        )

    monkeypatch.setattr(main.Orchestrator, "run_methodology_node_action", fake_run_methodology_node_action)

    adaptive = client.post(
        "/api/methodology/runtime/action",
        json={
            "methodology_id": "adaptive",
            "stage_id": "0.5-iteration-sprint-delivery-repeating-cycle",
            "activity_id": "0.5.1-sprint-iteration-planning",
            "lifecycle_event": "generate",
            "user_input": {"workspace_id": "demo-1"},
        },
    )
    predictive = client.post(
        "/api/methodology/runtime/action",
        json={
            "methodology_id": "predictive",
            "stage_id": "0.4-planning",
            "activity_id": "0.4.2-schedule-planning",
            "lifecycle_event": "generate",
            "user_input": {"workspace_id": "demo-1"},
        },
    )

    assert adaptive.status_code == 200
    assert predictive.status_code == 200
    assert captured[0]["template_ids"] == ["adaptive-software-dev"]
    assert captured[1]["template_ids"] == ["predictive-infrastructure"]


def test_runtime_action_publish_requires_human_review(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")

    async def fail_if_called(self, **kwargs):
        raise AssertionError("orchestrator should not run before human review approval")

    monkeypatch.setattr(main.Orchestrator, "run_methodology_node_action", fail_if_called)

    response = client.post(
        "/api/methodology/runtime/action",
        json={
            "methodology_id": "hybrid",
            "stage_id": "0.8-release-readiness-deployment-transition-gate-2-3-4-depending-on-model",
            "activity_id": "0.8.8-release-sign-off-and-gate-approval-to-proceed-close",
            "lifecycle_event": "publish",
            "user_input": {"workspace_id": "demo-1"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "review_required"
    assert payload["human_review"]["status"] == "pending"


def test_runtime_action_demo_mode_captures_external_side_effects_locally(client, monkeypatch, tmp_path):
    _set_tenant(monkeypatch, "demo-tenant")
    monkeypatch.setenv("DEMO_MODE", "true")
    from demo_integrations import DemoOutbox  # noqa: E402

    main.demo_outbox = DemoOutbox(tmp_path / "demo_outbox.json")

    async def fake_run_methodology_node_action(self, **kwargs):
        return OrchestrationResult(
            results={
                "task-1": {
                    "agent_id": "agent-09",
                    "metadata": {"template_id": "hybrid-infrastructure"},
                    "input": {
                        "connector_binding": {"connector_type": "jira"},
                        "side_effects": ["write_connector", "publish_external", "notify"],
                    },
                }
            },
            context={"correlation_id": "corr-demo"},
            metrics={"templates_executed": 1},
        )

    monkeypatch.setattr(main.Orchestrator, "run_methodology_node_action", fake_run_methodology_node_action)

    response = client.post(
        "/api/methodology/runtime/action",
        json={
            "methodology_id": "adaptive",
            "stage_id": "0.5-iteration-sprint-delivery-repeating-cycle",
            "activity_id": "0.5.1-sprint-iteration-planning",
            "lifecycle_event": "generate",
            "user_input": {"workspace_id": "demo-1", "human_review_approved": True},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"

    outbox = main.demo_outbox.read("external_side_effects")
    side_effects = {item["side_effect"] for item in outbox}
    assert {"write_connector", "publish_external", "notify"}.issubset(side_effects)
