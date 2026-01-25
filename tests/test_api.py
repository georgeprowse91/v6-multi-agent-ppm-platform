"""
Tests for FastAPI endpoints
"""

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
            "metadata": {"agent_id": "intent-router"},
        }
    )
    return mock


@pytest.mark.asyncio
async def test_root_endpoint(app):
    """Test root endpoint returns API info."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "Multi-Agent PPM Platform" in data["name"]


@pytest.mark.asyncio
async def test_health_endpoint(app):
    """Test health check endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_readiness_endpoint(app):
    """Test readiness check endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert "ready" in data
    assert "checks" in data


@pytest.mark.asyncio
async def test_liveness_endpoint(app):
    """Test liveness check endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["alive"] is True


@pytest.mark.asyncio
async def test_list_agents_endpoint(app, mock_orchestrator):
    """Test listing all agents."""
    with patch("api.main.orchestrator", mock_orchestrator):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/agents")

    assert response.status_code == 200
    data = response.json()
    assert "total_agents" in data
    assert "agents" in data


@pytest.mark.asyncio
async def test_query_endpoint(app, mock_orchestrator):
    """Test query processing endpoint."""
    with patch("api.main.orchestrator", mock_orchestrator):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/query",
                json={
                    "query": "Show me the portfolio overview",
                    "context": {"user_id": "test_user"},
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert "success" in data


@pytest.mark.asyncio
async def test_query_endpoint_validation(app):
    """Test query endpoint validates input."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Missing query field
        response = await client.post("/api/v1/query", json={"context": {}})

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_status_endpoint(app):
    """Test platform status endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/status")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "orchestrator_initialized" in data
