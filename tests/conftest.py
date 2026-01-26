"""
Pytest configuration and fixtures for Multi-Agent PPM Platform tests.
"""

import asyncio
import inspect
import sys
from pathlib import Path

import jwt
import pytest


def _bootstrap_paths() -> None:
    root = Path(__file__).resolve().parents[1]
    candidate_paths = [root]

    for base in ("apps", "services", "agents", "packages"):
        base_path = root / base
        if base_path.exists():
            candidate_paths.extend(path for path in base_path.glob("*/src") if path.is_dir())

    agents_path = root / "agents"
    if agents_path.exists():
        candidate_paths.extend(path for path in agents_path.glob("**/src") if path.is_dir())

    runtime_src = agents_path / "runtime" / "src"
    if runtime_src.exists():
        candidate_paths.append(runtime_src)

    for path in candidate_paths:
        path_str = str(path.resolve())
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


_bootstrap_paths()

try:
    import pytest_asyncio  # noqa: F401

    _HAS_PYTEST_ASYNCIO = True
except ModuleNotFoundError:
    _HAS_PYTEST_ASYNCIO = False


def pytest_pyfunc_call(pyfuncitem):
    if _HAS_PYTEST_ASYNCIO:
        return None
    if asyncio.iscoroutinefunction(pyfuncitem.obj):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        sig = inspect.signature(pyfuncitem.obj)
        kwargs = {name: pyfuncitem.funcargs[name] for name in sig.parameters}
        loop.run_until_complete(pyfuncitem.obj(**kwargs))
        loop.close()
        return True
    return None


# Configure event loop for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_azure_openai():
    """Mock Azure OpenAI client for testing."""
    # Future work: Implement Azure OpenAI mock
    pass


@pytest.fixture
def mock_database():
    """Mock database connection for testing."""
    # Future work: Implement database mock
    pass


@pytest.fixture
def mock_redis():
    """Mock Redis connection for testing."""
    # Future work: Implement Redis mock
    pass


@pytest.fixture
async def orchestrator():
    """Create and initialize an orchestrator instance for testing."""
    _bootstrap_paths()
    from orchestrator import AgentOrchestrator

    orch = AgentOrchestrator()
    await orch.initialize()

    yield orch

    await orch.cleanup()


@pytest.fixture
def sample_query():
    """Sample query for testing intent routing."""
    return "Show me the budget variance for Project Apollo"


@pytest.fixture
def sample_context():
    """Sample context for testing."""
    return {
        "user_id": "test_user",
        "session_id": "test_session",
        "timestamp": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def auth_headers(monkeypatch):
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    token = jwt.encode(
        {
            "sub": "user-123",
            "roles": ["portfolio_admin"],
            "aud": "ppm-platform",
            "iss": "https://issuer.example.com",
            "tenant_id": "tenant-alpha",
        },
        "test-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"}
