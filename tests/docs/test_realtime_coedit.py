from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

pytest.importorskip("cryptography")

SERVICE_ROOT = Path(__file__).resolve().parents[2] / "services" / "realtime-coedit-service"
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

spec = spec_from_file_location("realtime_coedit_main", MODULE_PATH)
assert spec and spec.loader
module = module_from_spec(spec)
SRC_PATH = str(SERVICE_ROOT / "src")
sys.path.insert(0, SRC_PATH)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
if SRC_PATH in sys.path:
    sys.path.remove(SRC_PATH)
# Purge any modules loaded from the temporary SRC_PATH to avoid
# polluting sys.modules for other test modules (e.g. data-lineage-service
# has its own 'storage' module with a different API).
for _mod_name in list(sys.modules):
    _mod = sys.modules[_mod_name]
    _mod_file = getattr(_mod, "__file__", None) or ""
    if _mod_name != spec.name and _mod_file.startswith(SRC_PATH):
        del sys.modules[_mod_name]


def _configure_auth(monkeypatch, tenant_id: str = "tenant-test") -> str:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    return jwt.encode(
        {
            "sub": "user-123",
            "roles": ["portfolio_admin"],
            "aud": "ppm-platform",
            "iss": "https://issuer.example.com",
            "tenant_id": tenant_id,
        },
        "test-secret",
        algorithm="HS256",
    )


def _wait_for_message(socket, message_type: str) -> dict:
    for _ in range(6):
        payload = socket.receive_json()
        if payload.get("type") == message_type:
            return payload
    raise AssertionError(f"Did not receive {message_type} message")


def test_realtime_coedit_two_users_sync(monkeypatch) -> None:
    token = _configure_auth(monkeypatch)

    with TestClient(module.app) as client:
        session_response = client.post(
            "/v1/sessions",
            json={"document_id": "doc-123", "initial_content": "Hello"},
            headers={"X-Tenant-ID": "tenant-test", "Authorization": f"Bearer {token}"},
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["session_id"]

        with client.websocket_connect(
            f"/v1/ws/documents/doc-123?session_id={session_id}&user_id=user-a&user_name=Alice"
        ) as ws_a:
            state_a = _wait_for_message(ws_a, "session_state")
            assert state_a["content"] == "Hello"

            with client.websocket_connect(
                f"/v1/ws/documents/doc-123?session_id={session_id}&user_id=user-b&user_name=Ben"
            ) as ws_b:
                state_b = _wait_for_message(ws_b, "session_state")
                assert state_b["content"] == "Hello"

                ws_a.send_json(
                    {
                        "type": "content_update",
                        "content": "Hello from Alice",
                        "base_version": state_a["version"],
                    }
                )
                update_b = _wait_for_message(ws_b, "content_update")
                assert update_b["content"] == "Hello from Alice"

                ws_b.send_json(
                    {
                        "type": "content_update",
                        "content": "Hello from Ben",
                        "base_version": state_b["version"],
                    }
                )
                update_a = _wait_for_message(ws_a, "content_update")
                assert "Hello from Alice" in update_a["content"]
                assert "Hello from Ben" in update_a["content"]
