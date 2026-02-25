"""Tests for SecurityHeadersMiddleware.

Covers:
- Content-Security-Policy (CSP) header presence and correctness
- HSTS header behaviour (only on HTTPS)
- Other mandatory security headers
- CSP extension via CSP_EXTRA_SCRIPT_SRCS environment variable
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure the security package is importable in the test environment.
_SECURITY_SRC = Path(__file__).resolve().parents[2] / "packages" / "security" / "src"
if str(_SECURITY_SRC) not in sys.path:
    sys.path.insert(0, str(_SECURITY_SRC))

from security.headers import SecurityHeadersMiddleware, _build_csp  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _app_with_middleware(**middleware_kwargs) -> FastAPI:
    """Build a minimal FastAPI app wrapped with SecurityHeadersMiddleware."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, **middleware_kwargs)

    @app.get("/ping")
    async def ping() -> dict:
        return {"ok": True}

    return app


# ---------------------------------------------------------------------------
# CSP construction
# ---------------------------------------------------------------------------


def test_build_csp_default_contains_required_directives() -> None:
    csp = _build_csp()
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp
    assert "base-uri 'self'" in csp
    assert "form-action 'self'" in csp
    assert "upgrade-insecure-requests" in csp


def test_build_csp_extra_script_srcs_appended() -> None:
    csp = _build_csp("https://cdn.example.com")
    # The extra host must appear inside the script-src directive.
    assert "script-src 'self' https://cdn.example.com" in csp
    # Other directives must still be present.
    assert "object-src 'none'" in csp


def test_build_csp_without_extra_script_srcs_has_self_only() -> None:
    csp = _build_csp(None)
    assert "script-src 'self'" in csp
    # Must NOT contain any bare host beyond 'self' in the script-src directive.
    script_directive = next(d for d in csp.split(";") if d.strip().startswith("script-src"))
    assert script_directive.strip() == "script-src 'self'"


# ---------------------------------------------------------------------------
# Header presence
# ---------------------------------------------------------------------------


def test_csp_header_present_on_response() -> None:
    client = TestClient(_app_with_middleware())
    response = client.get("/ping")
    assert response.status_code == 200
    assert "content-security-policy" in response.headers


def test_csp_header_value_matches_built_policy() -> None:
    client = TestClient(_app_with_middleware())
    response = client.get("/ping")
    expected = _build_csp(None)
    assert response.headers["content-security-policy"] == expected


def test_mandatory_headers_all_present() -> None:
    client = TestClient(_app_with_middleware())
    response = client.get("/ping")
    headers = response.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("referrer-policy") == "no-referrer"
    assert "permissions-policy" in headers
    assert headers.get("cross-origin-opener-policy") == "same-origin"
    assert headers.get("cross-origin-resource-policy") == "same-origin"


# ---------------------------------------------------------------------------
# HSTS
# ---------------------------------------------------------------------------


def test_hsts_not_added_for_http_requests() -> None:
    client = TestClient(_app_with_middleware(enable_hsts=True))
    response = client.get("/ping")
    # TestClient uses http:// by default, so HSTS must not be set.
    assert "strict-transport-security" not in response.headers


def test_hsts_disabled_when_enable_hsts_false() -> None:
    client = TestClient(_app_with_middleware(enable_hsts=False))
    response = client.get("/ping")
    assert "strict-transport-security" not in response.headers


# ---------------------------------------------------------------------------
# CSP via environment variable
# ---------------------------------------------------------------------------


def test_csp_extra_sources_via_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CSP_EXTRA_SCRIPT_SRCS", "https://analytics.example.com")
    client = TestClient(_app_with_middleware())
    response = client.get("/ping")
    csp = response.headers["content-security-policy"]
    assert "https://analytics.example.com" in csp
