from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from runtime import ConnectorActionClient, ConnectorActionRuntimeError, ConnectorRegistry


class _Module:
    def __init__(self, fn):
        self.execute_action = fn


def _build_registry(tmp_path: Path) -> ConnectorRegistry:
    connector_root = tmp_path / "demo"
    (connector_root / "src").mkdir(parents=True)
    (connector_root / "manifest.yaml").write_text("id: demo\n")
    (connector_root / "src" / "main.py").write_text(
        "def execute_action(action, payload, context):\n    return {'status': 'completed', 'data': payload, 'errors': []}\n"
    )
    registry_path = tmp_path / "connectors.json"
    registry_path.write_text(
        json.dumps(
            [
                {
                    "id": "demo",
                    "name": "Demo",
                    "manifest_path": str(connector_root / "manifest.yaml"),
                    "status": "beta",
                    "certification": "none",
                }
            ]
        )
    )
    return ConnectorRegistry(registry_path=registry_path)


@pytest.mark.anyio
async def test_successful_action_execution(tmp_path: Path) -> None:
    client = ConnectorActionClient(_build_registry(tmp_path))
    result = await client.execute(connector_id="demo", action="test_action", payload={"ok": True})
    assert result["status"] == "completed"
    assert result["data"] == {"ok": True}
    assert result["connector_id"] == "demo"
    assert result["action"] == "test_action"


@pytest.mark.anyio
async def test_unknown_connector(tmp_path: Path) -> None:
    client = ConnectorActionClient(_build_registry(tmp_path))
    with pytest.raises(ConnectorActionRuntimeError) as exc:
        await client.execute(connector_id="missing", action="noop", payload={})
    assert exc.value.code == "not_found"


@pytest.mark.anyio
async def test_connector_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def slow(**_: object) -> dict[str, object]:
        import asyncio

        await asyncio.sleep(0.05)
        return {"status": "completed", "data": {}, "errors": []}

    client = ConnectorActionClient(_build_registry(tmp_path), timeout_seconds=0.01, max_retries=0)
    monkeypatch.setattr(client, "_load_entrypoint_module", lambda _connector: _Module(slow))
    with pytest.raises(ConnectorActionRuntimeError) as exc:
        await client.execute(connector_id="demo", action="slow", payload={})
    assert exc.value.code == "timeout"


@pytest.mark.anyio
async def test_connector_auth_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def auth_fail(**_: object) -> dict[str, object]:
        raise PermissionError("unauthorized")

    client = ConnectorActionClient(_build_registry(tmp_path), max_retries=0)
    monkeypatch.setattr(client, "_load_entrypoint_module", lambda _connector: _Module(auth_fail))
    with pytest.raises(ConnectorActionRuntimeError) as exc:
        await client.execute(connector_id="demo", action="secured", payload={})
    assert exc.value.code == "auth_failed"


@pytest.mark.anyio
async def test_retry_exhausted_behavior(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"count": 0}

    def always_fail(**_: object) -> dict[str, object]:
        attempts["count"] += 1
        raise RuntimeError("upstream down")

    client = ConnectorActionClient(
        _build_registry(tmp_path), max_retries=1, retry_initial_delay_seconds=0
    )
    monkeypatch.setattr(client, "_load_entrypoint_module", lambda _connector: _Module(always_fail))
    with pytest.raises(ConnectorActionRuntimeError) as exc:
        await client.execute(connector_id="demo", action="unstable", payload={})
    assert exc.value.code == "upstream_unavailable"
    assert attempts["count"] == 2


@pytest.mark.anyio
async def test_output_contract_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def invalid_output(**_: object) -> dict[str, object]:
        return {"status": "completed", "data": {}, "errors": "bad"}

    client = ConnectorActionClient(_build_registry(tmp_path), max_retries=0)
    monkeypatch.setattr(
        client, "_load_entrypoint_module", lambda _connector: _Module(invalid_output)
    )
    with pytest.raises(ConnectorActionRuntimeError) as exc:
        await client.execute(connector_id="demo", action="bad_output", payload={})
    assert exc.value.code == "validation_failed"
