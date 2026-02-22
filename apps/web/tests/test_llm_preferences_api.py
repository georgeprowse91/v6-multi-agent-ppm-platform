import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
MODULE_PATH = SRC_DIR / "main.py"
spec = spec_from_file_location("web_main_llm_prefs", MODULE_PATH)
assert spec and spec.loader
main = module_from_spec(spec)
sys.modules[spec.name] = main
spec.loader.exec_module(main)
from llm_preferences_store import LLMPreferencesStore  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", "tenant-a")
    main.llm_preferences_store = LLMPreferencesStore(tmp_path / "llm_preferences.json")
    return TestClient(main.app)


def test_preferences_resolution_order(client):
    client.post(
        "/v1/api/llm/preferences",
        json={"scope": "tenant", "provider": "openai", "model_id": "gpt-4o-mini"},
    )
    client.post(
        "/v1/api/llm/preferences",
        json={
            "scope": "project",
            "project_id": "proj-1",
            "provider": "anthropic",
            "model_id": "claude-3-5-haiku-latest",
        },
    )
    client.post(
        "/v1/api/llm/preferences",
        json={"scope": "user", "provider": "google", "model_id": "gemini-1.5-flash"},
    )

    response = client.get("/v1/api/llm/preferences", params={"project_id": "proj-1"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "google"
    assert payload["model_id"] == "gemini-1.5-flash"


def test_project_defaults_are_rbac_gated(client, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_ROLES", "TEAM_MEMBER")
    response = client.post(
        "/v1/api/llm/preferences",
        json={
            "scope": "project",
            "project_id": "proj-1",
            "provider": "openai",
            "model_id": "gpt-4o-mini",
        },
    )
    assert response.status_code == 403
