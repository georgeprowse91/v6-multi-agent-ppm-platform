from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import httpx
import jwt

REPO_ROOT = Path(__file__).resolve().parents[2]


async def _run() -> None:
    examples = REPO_ROOT / "examples" / "demo-scenarios"

    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("AUTH_DEV_MODE", "true")
    os.environ.setdefault("AUTH_DEV_ROLES", "tenant_owner")
    os.environ.setdefault("AUTH_DEV_TENANT_ID", "dev-tenant")
    os.environ.setdefault("LLM_PROVIDER", "mock")
    os.environ.setdefault(
        "LLM_MOCK_RESPONSE_PATH", str(examples / "quickstart-llm-response.json")
    )
    os.environ.setdefault("IDENTITY_JWT_SECRET", "dev-secret")

    token = jwt.encode(
        {"tenant_id": "dev-tenant", "roles": ["tenant_owner"], "sub": "quickstart-user"},
        os.environ["IDENTITY_JWT_SECRET"],
        algorithm="HS256",
    )

    api_root = REPO_ROOT / "apps" / "api-gateway" / "src"
    package_src_roots = sorted((REPO_ROOT / "packages").glob("*/src"))
    agent_src_roots = sorted((REPO_ROOT / "agents").glob("**/src"))
    service_src_roots = sorted((REPO_ROOT / "services").glob("**/src"))
    connector_sdk_root = REPO_ROOT / "integrations" / "connectors" / "sdk" / "src"
    for root in (
        api_root,
        connector_sdk_root,
        *package_src_roots,
        *agent_src_roots,
        *service_src_roots,
        REPO_ROOT,
    ):
        if str(root) not in sys.path:
            sys.path.append(str(root))

    from api.main import app as api_app  # noqa: WPS433

    has_slowapi_middleware = any(
        "SlowAPIMiddleware" in middleware.cls.__name__
        for middleware in getattr(api_app, "user_middleware", [])
    )
    assert has_slowapi_middleware, "SlowAPI middleware should be registered"

    headers = {
        "X-Tenant-ID": "dev-tenant",
        "Authorization": f"Bearer {token}",
    }
    async with httpx.AsyncClient(app=api_app, base_url="http://api") as api_client:
        response = await api_client.get("/healthz", headers=headers)
        response.raise_for_status()
        payload = response.json()

    assert payload["status"] == "ok", payload


if __name__ == "__main__":
    asyncio.run(_run())
