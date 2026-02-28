from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[4]
SDK_PATH = REPO_ROOT / "connectors" / "sdk" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from auth import OAuth2TokenManager
from http_client import HttpClient


class QueueTransport(httpx.BaseTransport):
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = responses

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        payload = self._responses.pop(0)
        return httpx.Response(
            status_code=payload.get("status_code", 200),
            json=payload.get("json", {}),
            request=request,
        )


def test_oauth_token_refresh_on_expiry(monkeypatch):
    responses = [
        {"json": {"access_token": "token-1", "refresh_token": "refresh-1", "expires_in": 1}},
        {"json": {"access_token": "token-2", "refresh_token": "refresh-2", "expires_in": 3600}},
    ]
    transport = QueueTransport(responses)
    client = HttpClient(base_url="https://auth.example.com", transport=transport)
    manager = OAuth2TokenManager(
        token_url="/oauth/token",
        client_id="client-id",
        client_secret="client-secret",
        refresh_token="refresh-0",
        http_client=client,
        expiry_buffer_seconds=0,
    )

    monkeypatch.setattr("auth.time.time", lambda: 1000.0)
    assert manager.get_access_token() == "token-1"

    monkeypatch.setattr("auth.time.time", lambda: 1002.0)
    assert manager.get_access_token() == "token-2"
