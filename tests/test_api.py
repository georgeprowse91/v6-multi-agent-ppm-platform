"""
Tests for FastAPI endpoints
"""

import asyncio
import importlib
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    from api.main import app

    return app


@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator for testing."""
    mock = MagicMock()
    mock.initialized = True
    mock.get_agent_count.return_value = 25
    mock.list_agents.return_value = [
        {"agent_id": "test-agent", "name": "Test Agent", "status": "active"}
    ]
    mock.process_query = AsyncMock(
        return_value={
            "success": True,
            "data": {"response": "Test response"},
            "metadata": {
                "agent_id": "intent-router",
                "catalog_id": "intent-router",
                "timestamp": "2024-01-01T00:00:00Z",
                "correlation_id": "test-corr-id",
            },
        }
    )
    return mock


@pytest.mark.asyncio
async def test_root_endpoint(app, auth_headers):
    """Test root endpoint returns API info."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "Multi-Agent PPM Platform" in data["name"]


@pytest.mark.asyncio
async def test_healthz_endpoint(app, auth_headers):
    """Test healthz endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/healthz", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_endpoint(app, auth_headers):
    """Test health check endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/health", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_version_endpoint(app, auth_headers):
    """Test version endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/version", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "multi-agent-ppm-api"
    assert "version" in data


@pytest.mark.asyncio
async def test_readiness_endpoint(app, auth_headers):
    """Test readiness check endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/health/ready", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "ready" in data
    assert "checks" in data


@pytest.mark.asyncio
async def test_liveness_endpoint(app, auth_headers):
    """Test liveness check endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/health/live", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["alive"] is True


@pytest.mark.asyncio
async def test_list_agents_endpoint(app, mock_orchestrator, auth_headers):
    """Test listing all agents."""
    with patch("api.main.orchestrator", mock_orchestrator):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/agents", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "total_agents" in data
    assert "agents" in data


@pytest.mark.asyncio
async def test_query_endpoint(app, mock_orchestrator, auth_headers):
    """Test query processing endpoint."""
    with patch("api.main.orchestrator", mock_orchestrator):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/query",
                json={
                    "query": "Show me the portfolio overview",
                    "context": {"user_id": "test_user"},
                },
                headers=auth_headers,
            )

    assert response.status_code == 200
    data = response.json()
    assert "success" in data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"context": {}},  # missing query
        {"query": 123, "context": {}},  # wrong type
        {"query": "Show me risks", "context": "not-a-dict"},  # schema violation
    ],
)
async def test_query_endpoint_validation(app, auth_headers, payload):
    """Test query endpoint validates malformed and schema-invalid inputs."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/query", json=payload, headers=auth_headers)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers",
    [
        {},  # missing auth and tenant
        {"Authorization": "Bearer invalid-token", "X-Tenant-ID": "tenant-alpha"},
        {"X-Tenant-ID": "tenant-alpha"},  # missing credentials
    ],
)
async def test_query_endpoint_auth_failures(app, headers):
    """Test query endpoint rejects missing/invalid credentials."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/query", json={"query": "show status"}, headers=headers)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_query_endpoint_expired_credentials(app, monkeypatch):
    """Test query endpoint rejects expired JWT credentials."""
    import jwt

    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    expired_token = jwt.encode(
        {
            "sub": "user-123",
            "roles": ["portfolio_admin"],
            "aud": "ppm-platform",
            "iss": "https://issuer.example.com",
            "tenant_id": "tenant-alpha",
            "exp": 1,
        },
        "test-secret",
        algorithm="HS256",
    )
    headers = {"Authorization": f"Bearer {expired_token}", "X-Tenant-ID": "tenant-alpha"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/query", json={"query": "show status"}, headers=headers)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_upstream_timeout_returns_server_error(monkeypatch):
    """Test auth upstream timeout/unavailability propagates as server error."""
    monkeypatch.setenv("AUTH_SERVICE_URL", "http://identity.local")
    monkeypatch.setenv("ABAC_ENFORCEMENT", "false")

    sys.modules.pop("api.main", None)
    importlib.import_module("api.main")
    from api.main import app

    async def _timeout(*args, **kwargs):
        raise TimeoutError("upstream timeout")

    with patch("api.middleware.security.httpx.AsyncClient.post", side_effect=_timeout):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/query",
                json={"query": "show status"},
                headers={"Authorization": "Bearer any", "X-Tenant-ID": "tenant-alpha"},
            )

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_rate_limit_under_concurrent_requests(monkeypatch, auth_headers):
    """Test rate limiting behavior under concurrent request stress."""
    monkeypatch.setenv("RATE_LIMIT_DEFAULT", "1/minute")
    monkeypatch.setenv("RATE_LIMIT_STORAGE", "memory://")

    sys.modules.pop("api.main", None)
    sys.modules.pop("api.limiter", None)
    from api.main import app

    async def _get_status(client):
        return await client.get("/v1/status", headers=auth_headers)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        responses = await asyncio.gather(*[_get_status(client) for _ in range(8)])

    statuses = [response.status_code for response in responses]
    assert statuses.count(200) == 1
    assert statuses.count(429) == 7


@pytest.mark.asyncio
async def test_status_endpoint(app, auth_headers):
    """Test platform status endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/status", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "orchestrator_initialized" in data
