from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

WEB_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = WEB_ROOT / "src" / "main.py"


def _load_web_module():
    sys.path.insert(0, str(WEB_ROOT / "src"))
    spec = spec_from_file_location("web_main_oidc", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _build_oidc_transport(issuer: str, nonce_holder: dict[str, str]) -> httpx.MockTransport:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key())
    public_payload = json.loads(public_jwk)
    public_payload["kid"] = "test-key"
    jwks = {"keys": [public_payload]}

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/.well-known/openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "issuer": issuer,
                    "authorization_endpoint": f"{issuer}/authorize",
                    "token_endpoint": f"{issuer}/token",
                    "jwks_uri": f"{issuer}/jwks",
                    "end_session_endpoint": f"{issuer}/logout",
                },
            )
        if request.url.path.endswith("/token"):
            now = datetime.now(timezone.utc)
            claims = {
                "sub": "user-123",
                "tenant_id": "tenant-abc",
                "roles": ["PMO_ADMIN", "PM"],
                "nonce": nonce_holder["value"],
                "iss": issuer,
                "aud": os.environ["OIDC_CLIENT_ID"],
                "exp": int((now + timedelta(minutes=5)).timestamp()),
                "iat": int(now.timestamp()),
            }
            id_token = jwt.encode(
                claims,
                private_key,
                algorithm="RS256",
                headers={"kid": "test-key"},
            )
            return httpx.Response(200, json={"access_token": "access-token", "id_token": id_token})
        if request.url.path.endswith("/jwks"):
            return httpx.Response(200, json=jwks)
        return httpx.Response(404, json={"detail": "not found"})

    return httpx.MockTransport(handler)


def test_oidc_login_flow_sets_session_cookie():
    os.environ["OIDC_ISSUER_URL"] = "https://issuer.example.com"
    os.environ["OIDC_CLIENT_ID"] = "client-123"
    os.environ["OIDC_CLIENT_SECRET"] = "env:OIDC_SECRET"
    os.environ["OIDC_SECRET"] = "client-secret"
    os.environ["OIDC_REDIRECT_URI"] = "http://localhost/oidc/callback"
    os.environ["AUTH_SESSION_SIGNING_KEY"] = "env:SESSION_KEY"
    os.environ["SESSION_KEY"] = "session-secret"
    os.environ["ENVIRONMENT"] = "test"

    nonce_holder: dict[str, str] = {}
    transport = _build_oidc_transport(os.environ["OIDC_ISSUER_URL"], nonce_holder)

    module = _load_web_module()
    module.OIDC_HTTP_TRANSPORT = transport
    client = TestClient(module.app)

    response = client.get("/login", allow_redirects=False)
    assert response.status_code in {302, 307}
    location = response.headers["location"]
    params = parse_qs(urlparse(location).query)
    state = params["state"][0]
    nonce = params["nonce"][0]
    nonce_holder["value"] = nonce

    state_cookie = response.cookies.get("ppm_oidc_state")
    assert state_cookie
    state_payload = jwt.decode(
        state_cookie,
        os.environ["SESSION_KEY"],
        algorithms=["HS256"],
        options={"verify_aud": False, "verify_iss": False},
    )
    assert state_payload["state"] == state
    assert state_payload["nonce"] == nonce

    callback = client.get(f"/oidc/callback?code=auth-code&state={state}", allow_redirects=False)
    assert callback.status_code in {302, 307}
    assert callback.headers["location"] == "/app"

    session_info = client.get("/session")
    payload = session_info.json()
    assert payload["authenticated"] is True
    assert payload["tenant_id"] == "tenant-abc"
    assert set(payload["roles"]) == {"PMO_ADMIN", "PM"}



def test_oidc_callback_redirects_project_context_to_spa_route():
    os.environ["OIDC_ISSUER_URL"] = "https://issuer.example.com"
    os.environ["OIDC_CLIENT_ID"] = "client-123"
    os.environ["OIDC_CLIENT_SECRET"] = "env:OIDC_SECRET"
    os.environ["OIDC_SECRET"] = "client-secret"
    os.environ["OIDC_REDIRECT_URI"] = "http://localhost/oidc/callback"
    os.environ["AUTH_SESSION_SIGNING_KEY"] = "env:SESSION_KEY"
    os.environ["SESSION_KEY"] = "session-secret"
    os.environ["ENVIRONMENT"] = "test"

    nonce_holder: dict[str, str] = {}
    transport = _build_oidc_transport(os.environ["OIDC_ISSUER_URL"], nonce_holder)

    module = _load_web_module()
    module.OIDC_HTTP_TRANSPORT = transport
    client = TestClient(module.app)

    response = client.get("/login?project_id=crm-migration", allow_redirects=False)
    location = response.headers["location"]
    params = parse_qs(urlparse(location).query)
    state = params["state"][0]
    nonce_holder["value"] = params["nonce"][0]

    callback = client.get(f"/oidc/callback?code=auth-code&state={state}", allow_redirects=False)
    assert callback.status_code in {302, 307}
    assert callback.headers["location"] == "/app/projects/crm-migration"


def test_oidc_callback_redirects_return_to_spa_route_directly():
    os.environ["OIDC_ISSUER_URL"] = "https://issuer.example.com"
    os.environ["OIDC_CLIENT_ID"] = "client-123"
    os.environ["OIDC_CLIENT_SECRET"] = "env:OIDC_SECRET"
    os.environ["OIDC_SECRET"] = "client-secret"
    os.environ["OIDC_REDIRECT_URI"] = "http://localhost/oidc/callback"
    os.environ["AUTH_SESSION_SIGNING_KEY"] = "env:SESSION_KEY"
    os.environ["SESSION_KEY"] = "session-secret"
    os.environ["ENVIRONMENT"] = "test"

    nonce_holder: dict[str, str] = {}
    transport = _build_oidc_transport(os.environ["OIDC_ISSUER_URL"], nonce_holder)

    module = _load_web_module()
    module.OIDC_HTTP_TRANSPORT = transport
    client = TestClient(module.app)

    response = client.get(
        "/login?return_to=/app/projects/data-lake-uplift",
        allow_redirects=False,
    )
    location = response.headers["location"]
    params = parse_qs(urlparse(location).query)
    state = params["state"][0]
    nonce_holder["value"] = params["nonce"][0]

    callback = client.get(f"/oidc/callback?code=auth-code&state={state}", allow_redirects=False)
    assert callback.status_code in {302, 307}
    assert callback.headers["location"] == "/app/projects/data-lake-uplift"


def test_login_dev_auth_shortcut_redirects_to_spa(monkeypatch):
    monkeypatch.delenv("OIDC_ISSUER_URL", raising=False)
    monkeypatch.delenv("OIDC_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("AUTH_DEV_MODE", "true")

    module = _load_web_module()
    client = TestClient(module.app)

    response = client.get("/login", allow_redirects=False)
    assert response.status_code in {302, 307}
    assert response.headers["location"] == "/app"
