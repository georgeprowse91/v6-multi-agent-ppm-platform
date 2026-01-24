"""
Tests for FastAPI endpoints
"""

import pytest
from httpx import AsyncClient


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    from src.api.main import app
    return app


@pytest.mark.asyncio
async def test_root_endpoint(app):
    """Test root endpoint returns API info."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "Multi-Agent PPM Platform" in data["name"]


@pytest.mark.asyncio
async def test_health_endpoint(app):
    """Test health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_readiness_endpoint(app):
    """Test readiness check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert "ready" in data
    assert "checks" in data


@pytest.mark.asyncio
async def test_liveness_endpoint(app):
    """Test liveness check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["alive"] is True


@pytest.mark.asyncio
async def test_list_agents_endpoint(app):
    """Test listing all agents."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/agents")

    assert response.status_code == 200
    data = response.json()
    assert "total_agents" in data
    assert "agents" in data


@pytest.mark.asyncio
async def test_query_endpoint(app):
    """Test query processing endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/query",
            json={
                "query": "Show me the portfolio overview",
                "context": {"user_id": "test_user"}
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert "success" in data


@pytest.mark.asyncio
async def test_query_endpoint_validation(app):
    """Test query endpoint validates input."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Missing query field
        response = await client.post(
            "/api/v1/query",
            json={"context": {}}
        )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_status_endpoint(app):
    """Test platform status endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/status")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "orchestrator_initialized" in data
