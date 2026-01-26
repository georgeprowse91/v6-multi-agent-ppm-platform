from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

sys.path.insert(0, str(SERVICE_ROOT / "src"))

spec = spec_from_file_location("policy_engine_main", MODULE_PATH)
module = module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)

client = TestClient(module.app)


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "policy-engine"


def test_policy_evaluate_allow() -> None:
    bundle = {
        "apiVersion": "ppm.policies/v1",
        "kind": "PolicyBundle",
        "metadata": {"name": "demo", "version": "1.0.0", "owner": "qa"},
        "policies": [],
    }
    response = client.post("/policies/evaluate", json={"bundle": bundle})
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "allow"
