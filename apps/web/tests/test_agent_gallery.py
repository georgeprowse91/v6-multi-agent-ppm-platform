import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import main  # noqa: E402
from agent_settings_store import AgentSettingsStore  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    main.agent_settings_store = AgentSettingsStore(tmp_path / "agent_settings.json")
    return TestClient(main.app)


def _set_tenant(monkeypatch, tenant_id: str) -> None:
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", tenant_id)


def _set_roles(monkeypatch, roles: str) -> None:
    monkeypatch.setenv("AUTH_DEV_ROLES", roles)


def test_registry_lists_agents_from_repo_evidence(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.get("/api/agent-gallery/agents")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 25
    assert any(entry["agent_id"] == "intent-router" for entry in payload)


def test_project_settings_initialise_and_persist(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.get("/api/agent-gallery/demo-1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant_id"] == "tenant-a"
    assert payload["project_id"] == "demo-1"
    assert len(payload["agents"]) >= 25

    settings = main.agent_settings_store.get_project_settings("tenant-a", "demo-1")
    assert settings is not None
    assert settings.project_id == "demo-1"


def test_admin_can_toggle_and_configure(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    _set_roles(monkeypatch, "tenant_owner")
    response = client.get("/api/agent-gallery/demo-1")
    payload = response.json()
    target = next(agent for agent in payload["agents"] if not agent["required"])

    toggle_response = client.patch(
        f"/api/agent-gallery/demo-1/agents/{target['agent_id']}",
        json={"enabled": False},
    )
    assert toggle_response.status_code == 200
    assert toggle_response.json()["enabled"] is False

    config_payload = {"threshold": 0.7, "owner": "pm"}
    config_response = client.patch(
        f"/api/agent-gallery/demo-1/agents/{target['agent_id']}",
        json={"config": config_payload},
    )
    assert config_response.status_code == 200
    assert config_response.json()["config"] == config_payload

    refreshed = client.get("/api/agent-gallery/demo-1").json()
    updated = next(agent for agent in refreshed["agents"] if agent["agent_id"] == target["agent_id"])
    assert updated["enabled"] is False
    assert updated["config"] == config_payload


def test_non_admin_cannot_modify(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    _set_roles(monkeypatch, "project_viewer")
    response = client.patch(
        "/api/agent-gallery/demo-1/agents/intent-router",
        json={"enabled": False},
    )
    assert response.status_code == 403


def test_required_agent_cannot_be_disabled(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    _set_roles(monkeypatch, "tenant_owner")
    response = client.patch(
        "/api/agent-gallery/demo-1/agents/intent-router",
        json={"enabled": False},
    )
    assert response.status_code == 422


def test_tenant_isolation(client, monkeypatch):
    _set_roles(monkeypatch, "tenant_owner")
    _set_tenant(monkeypatch, "tenant-a")
    response = client.patch(
        "/api/agent-gallery/demo-1/agents/demand-intake",
        json={"enabled": False, "config": {"note": "tenant-a"}},
    )
    assert response.status_code == 200

    _set_tenant(monkeypatch, "tenant-b")
    response = client.get("/api/agent-gallery/demo-1")
    assert response.status_code == 200
    payload = response.json()
    agent = next(agent for agent in payload["agents"] if agent["agent_id"] == "demand-intake")
    assert agent["config"] in ({}, {"note": "tenant-b"})
    assert agent["enabled"] is True
