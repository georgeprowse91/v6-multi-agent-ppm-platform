import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
MODULE_PATH = SRC_DIR / "main.py"
spec = spec_from_file_location("web_main_portfolio", MODULE_PATH)
assert spec and spec.loader
main = module_from_spec(spec)
sys.modules[spec.name] = main
spec.loader.exec_module(main)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO_DIR = REPO_ROOT / "examples" / "demo-scenarios"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    return TestClient(main.app)


def test_portfolio_health_demo_payload(client, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    expected = json.loads((DEMO_DIR / "portfolio-health.json").read_text(encoding="utf-8"))

    response = client.get("/api/portfolio-health?project_id=demo-1")

    assert response.status_code == 200
    assert response.json() == expected


def test_lifecycle_metrics_demo_payload(client, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    expected = json.loads((DEMO_DIR / "lifecycle-metrics.json").read_text(encoding="utf-8"))

    response = client.get("/api/lifecycle-metrics?project_id=demo-1")

    assert response.status_code == 200
    assert response.json() == expected


def test_portfolio_health_mocked_when_not_demo(client, monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)

    response = client.get("/api/portfolio-health?project_id=demo-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == "demo-1"
    assert {kpi["id"] for kpi in payload["kpis"]} >= {
        "value_delivered",
        "budget_utilisation",
        "risk_exposure",
        "resource_capacity",
        "stage_gate_status",
    }


def test_lifecycle_metrics_mocked_when_not_demo(client, monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)

    response = client.get("/api/lifecycle-metrics?project_id=demo-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == "demo-1"
    assert payload["stage_gates"]
