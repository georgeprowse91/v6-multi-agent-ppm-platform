import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import main  # noqa: E402
from workspace_state_store import WorkspaceStateStore  # noqa: E402

from agents.runtime.src.orchestrator import OrchestrationResult  # noqa: E402


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
    response = client.get("/api/workspace/demo-1?methodology=predictive")
    assert response.status_code == 200
    payload = response.json()
    assert payload["methodology"] == "predictive"
    assert payload["methodology_map_summary"]["id"] == "predictive"


def test_get_workspace_rejects_unknown_methodology_query(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.get("/api/workspace/demo-1?methodology=unknown")
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
            results={
                "task-1": {
                    "agent_id": "schedule-planning-agent",
                    "metadata": {"template_id": "adaptive-software-dev"},
                    "input": {},
                }
            },
            context={"correlation_id": "corr-test"},
            metrics={"templates_executed": 1},
        )

    monkeypatch.setattr(
        main.Orchestrator, "run_methodology_node_action", fake_run_methodology_node_action
    )

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
    assert payload["workflow_trace"]["agent_ids_executed"] == ["schedule-planning-agent"]


def test_runtime_action_known_template_mappings(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    captured: list[dict[str, object]] = []

    async def fake_run_methodology_node_action(self, **kwargs):
        captured.append(kwargs)
        template_ids = kwargs.get("template_ids", [])
        template_id = template_ids[0] if template_ids else "unknown"
        return OrchestrationResult(
            results={
                "task-1": {
                    "agent_id": "schedule-planning-agent",
                    "metadata": {"template_id": template_id},
                    "input": {},
                }
            },
            context={"correlation_id": "corr-test"},
            metrics={"templates_executed": 1},
        )

    monkeypatch.setattr(
        main.Orchestrator, "run_methodology_node_action", fake_run_methodology_node_action
    )

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
            "activity_id": "0.4.2-schedule-planning-agent",
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


def test_runtime_action_demo_mode_captures_external_side_effects_locally(
    client, monkeypatch, tmp_path
):
    _set_tenant(monkeypatch, "demo-tenant")
    monkeypatch.setenv("DEMO_MODE", "true")
    from demo_integrations import DemoOutbox  # noqa: E402

    main.demo_outbox = DemoOutbox(tmp_path / "demo_outbox.json")

    async def fake_run_methodology_node_action(self, **kwargs):
        return OrchestrationResult(
            results={
                "task-1": {
                    "agent_id": "lifecycle-governance-agent",
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

    monkeypatch.setattr(
        main.Orchestrator, "run_methodology_node_action", fake_run_methodology_node_action
    )

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


def test_connector_configure_and_connection_health_in_demo_mode(client, monkeypatch, tmp_path):
    _set_tenant(monkeypatch, "tenant-a")
    monkeypatch.setenv("DEMO_MODE", "true")
    from demo_integrations import DemoOutbox  # noqa: E402

    main.demo_outbox = DemoOutbox(tmp_path / "demo_outbox_connectors.json")

    create_response = client.post(
        "/api/connector-gallery/instances",
        json={
            "connector_type_id": "jira",
            "version": "1.0.0",
            "enabled": True,
            "metadata": {"scope": "project"},
        },
    )
    assert create_response.status_code == 201
    connector_id = create_response.json()["connector_id"]

    update_response = client.patch(
        f"/api/connector-gallery/instances/{connector_id}",
        json={"enabled": False, "health_status": "healthy"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["enabled"] is False

    health_response = client.get(f"/api/connector-gallery/instances/{connector_id}/health")
    assert health_response.status_code == 200
    assert health_response.json()["healthy"] is True


def test_sor_publish_endpoint_writes_outbox_and_audit_event(client, monkeypatch, tmp_path):
    _set_tenant(monkeypatch, "demo-tenant")
    monkeypatch.setenv("DEMO_MODE", "true")
    from demo_integrations import DemoOutbox  # noqa: E402

    main.demo_outbox = DemoOutbox(tmp_path / "demo_outbox_sor_publish.json")

    response = client.post(
        "/api/methodology/runtime/sor/publish",
        json={
            "methodology_id": "adaptive",
            "stage_id": "0.5-iteration-sprint-delivery-repeating-cycle",
            "activity_id": "0.5.1-sprint-iteration-planning",
            "lifecycle_event": "publish",
            "workspace_id": "demo-1",
            "changes": {"field": "value"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outbox_entry"]["status"] == "captured_in_demo_outbox"

    outbox = main.demo_outbox.read("external_side_effects")
    assert outbox
    applied = main.demo_outbox.read("applied_changes")
    assert applied

    audit_events = main.get_audit_log_store().list_events("default", limit=50, offset=0)
    assert any(event["action"] == "demo.sor.publish.stubbed" for event in audit_events)


@pytest.mark.parametrize(
    "project_id,methodology_id",
    [
        ("demo-predictive", "predictive"),
        ("demo-adaptive", "adaptive"),
        ("demo-hybrid", "hybrid"),
    ],
)
def test_workspace_methodology_payloads_are_fully_populated(
    client, monkeypatch, project_id, methodology_id
):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.get(f"/api/workspace/{project_id}?methodology={methodology_id}")
    assert response.status_code == 200
    payload = response.json()
    summary = payload["methodology_map_summary"]

    assert summary["stages"], f"Expected stages for {methodology_id}"
    assert summary["monitoring"], f"Expected monitoring activities for {methodology_id}"
    assert len(summary["monitoring"]) >= 3

    assert all(stage["activities"] for stage in summary["stages"]), "No stage-only stubs allowed"

    def _has_nested(items):
        for item in items:
            children = item.get("children", [])
            if children:
                return True
            if _has_nested(children):
                return True
        return False

    nested_present = any(_has_nested(stage["activities"]) for stage in summary["stages"])
    assert nested_present, f"Expected nested activities for {methodology_id}"


def test_runtime_review_queue_and_decision_flow(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")

    async def fake_run_methodology_node_action(self, **kwargs):
        return OrchestrationResult(
            results={
                "task-1": {
                    "agent_id": "schedule-planning-agent",
                    "metadata": {"template_id": "adaptive-software-dev"},
                    "input": {},
                }
            },
            context={"correlation_id": "corr-test"},
            metrics={"templates_executed": 1},
        )

    monkeypatch.setattr(
        main.Orchestrator, "run_methodology_node_action", fake_run_methodology_node_action
    )

    review = client.post(
        "/api/methodology/runtime/action",
        json={
            "methodology_id": "adaptive",
            "stage_id": "0.5-iteration-sprint-delivery-repeating-cycle",
            "activity_id": "0.5.1-sprint-iteration-planning",
            "lifecycle_event": "review",
            "user_input": {"workspace_id": "demo-1"},
        },
    )
    assert review.status_code == 200
    payload = review.json()
    assert payload["status"] == "review_required"
    approval_id = payload["human_review"]["approval_id"]

    queue = client.get(
        "/api/methodology/runtime/approvals", params={"workspace_id": "demo-1", "status": "pending"}
    )
    assert queue.status_code == 200
    assert any(item["approval_id"] == approval_id for item in queue.json()["items"])

    decision = client.post(
        f"/api/methodology/runtime/approvals/{approval_id}/decision",
        json={"workspace_id": "demo-1", "decision": "approve", "notes": "LGTM"},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"


def test_runtime_action_persists_artifact_metadata(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")

    async def fake_run_methodology_node_action(self, **kwargs):
        return OrchestrationResult(
            results={
                "task-1": {
                    "agent_id": "schedule-planning-agent",
                    "metadata": {"template_id": "adaptive-software-dev"},
                    "input": {},
                }
            },
            context={"correlation_id": "corr-test"},
            metrics={"templates_executed": 1},
        )

    monkeypatch.setattr(
        main.Orchestrator, "run_methodology_node_action", fake_run_methodology_node_action
    )

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
    assert payload["artifacts_created"]
    assert payload["artifacts_created"][0]["status"] == "draft"


def test_workspace_select_accepts_new_canvas_tabs(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    for tab in [
        "board",
        "backlog",
        "gantt",
        "grid",
        "financial",
        "dependency_map",
        "roadmap",
        "approval",
    ]:
        response = client.post(
            "/api/workspace/demo-1/select",
            json={
                "current_stage_id": None,
                "current_activity_id": None,
                "current_canvas_tab": tab,
                "methodology": "adaptive",
            },
        )
        assert response.status_code == 200
        assert response.json()["current_canvas_tab"] == tab
