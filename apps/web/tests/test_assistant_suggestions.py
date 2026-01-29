import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
MODULE_PATH = SRC_DIR / "main.py"
spec = spec_from_file_location("web_main_assistant", MODULE_PATH)
assert spec and spec.loader
main = module_from_spec(spec)
sys.modules[spec.name] = main
spec.loader.exec_module(main)
from workspace_state_store import WorkspaceStateStore  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    main.workspace_state_store = WorkspaceStateStore(tmp_path / "workspace_state.json")
    return TestClient(main.app)


def _set_tenant(monkeypatch, tenant_id: str) -> None:
    monkeypatch.setenv("AUTH_DEV_TENANT_ID", tenant_id)


def test_assistant_suggestions_include_context(client, monkeypatch):
    _set_tenant(monkeypatch, "tenant-a")
    response = client.post(
        "/api/assistant/suggestions",
        json={
            "project_id": "demo-1",
            "activity_id": "agile-vision",
            "activity_name": "Product Vision Statement",
            "stage_id": "agile-discovery",
            "stage_name": "Discovery",
            "activity_status": "in_progress",
            "canvas_type": "document",
            "incomplete_prerequisites": [],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["context"]["activity_id"] == "agile-vision"
    assert payload["generated_by"] in {"llm", "heuristic"}
    assert payload["suggestions"]
