from __future__ import annotations

import sys
import os
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

spec = spec_from_file_location("data_sync_main", MODULE_PATH)
assert spec and spec.loader
module = module_from_spec(spec)
sys.path.insert(0, str(SERVICE_ROOT / "src"))
sys.modules[spec.name] = module
spec.loader.exec_module(module)

client = TestClient(module.app)


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "data-sync-service"


def test_sync_run_returns_rules() -> None:
    response = client.post("/v1/sync/run", json={"connector": "jira", "dry_run": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert "ds-001" in payload["planned_rules"]


def test_sync_run_rejects_malformed_yaml(monkeypatch, tmp_path) -> None:
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    bad_rule = rules_dir / "bad.yaml"
    bad_rule.write_text("id: [", encoding="utf-8")
    monkeypatch.setenv("DATA_SYNC_RULES_DIR", str(rules_dir))

    response = client.post("/v1/sync/run", json={"connector": "jira", "dry_run": True})
    assert response.status_code == 422
    payload = response.json()
    assert payload["detail"]["message"] == "Invalid rule files"
    assert any(item["path"] == str(bad_rule) for item in payload["detail"]["files"])


def test_sync_run_rejects_unreadable_rules(monkeypatch, tmp_path) -> None:
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    unreadable = rules_dir / "unreadable.yaml"
    unreadable.write_text("id: ds-999\nsource: s\ntarget: t\n", encoding="utf-8")
    unreadable.chmod(0)
    monkeypatch.setenv("DATA_SYNC_RULES_DIR", str(rules_dir))

    try:
        response = client.post("/v1/sync/run", json={"connector": "jira", "dry_run": True})
    finally:
        os.chmod(unreadable, 0o644)

    assert response.status_code == 422
    payload = response.json()
    assert payload["detail"]["message"] == "Invalid rule files"
    assert any(item["path"] == str(unreadable) for item in payload["detail"]["files"])
