import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _redis_available() -> bool:
    return importlib.util.find_spec("redis") is not None


@pytest.mark.skipif(not _redis_available(), reason="redis is not installed")
def test_list_agents():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "apps" / "orchestration-service" / "src" / "main.py"

    spec = importlib.util.spec_from_file_location("orchestration_service_main", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    app = module.app

    client = TestClient(app)
    resp = client.get("/v1/agents")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
