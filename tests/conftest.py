"""
Pytest configuration and fixtures for Multi-Agent PPM Platform tests.
"""

import asyncio
import collections
import importlib.util
import inspect
import os
import sys
from pathlib import Path

import jwt
import pytest


CI_OPTIONAL_TEST_DEPENDENCIES = {
    "api_security": ["slowapi"],
    "workflow_execution": ["celery"],
    "web_governance": ["email_validator"],
}

_MISSING_DEPENDENCY_SKIP_PATTERNS = (
    "is not installed",
    "no module named",
    "could not import",
    "module not found",
)
_PLATFORM_SKIP_PATTERNS = (
    "[platform]",
    "platform-specific",
    "platform specific",
    "unsupported platform",
    "requires linux",
    "requires macos",
    "requires windows",
)


_PYTEST_CONFIG = None


def _bootstrap_paths() -> None:
    root = Path(__file__).resolve().parents[1]
    candidate_paths = [root]

    for base in (
        "apps",
        "services",
        "agents",
        "packages",
        "integrations/apps",
        "integrations/connectors",
        "integrations/services",
    ):
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


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _jsonschema_has_validator() -> bool:
    if not _module_available("jsonschema"):
        return False
    import jsonschema

    validator = getattr(jsonschema, "Draft202012Validator", None)
    return validator is not None and hasattr(validator, "check_schema")


def pytest_ignore_collect(collection_path: Path, config):
    path_str = str(collection_path)
    if "tests/integration/connectors" in path_str and not os.getenv(
        "ENABLE_CONNECTOR_INTEGRATION_TESTS"
    ):
        return True
    if path_str.endswith("tests/test_api.py") and not _module_available("slowapi"):
        return True
    if path_str.endswith("tests/contract/test_api_contract.py") and not _module_available(
        "slowapi"
    ):
        return True
    if path_str.endswith("tests/load/test_load_sla.py") and not _module_available("slowapi"):
        return True
    if path_str.endswith("tests/security/test_auth_rbac.py") and not _module_available("slowapi"):
        return True
    if path_str.endswith(
        "tests/security/test_agent_config_rbac.py"
    ) and not _module_available("slowapi"):
        return True
    if path_str.endswith("tests/security/test_field_level_masking.py") and not _module_available(
        "slowapi"
    ):
        return True
    if path_str.endswith("tests/security/test_rate_limit_cors.py") and not _module_available(
        "slowapi"
    ):
        return True
    if path_str.endswith(
        "tests/security/test_policy_engine_integration.py"
    ) and not _module_available("cryptography"):
        return True
    if path_str.endswith("tests/security/test_downstream_auth.py") and (
        not _module_available("cryptography") or not _module_available("azure")
    ):
        return True
    if path_str.endswith("tests/e2e/test_acceptance_scenarios.py") and (
        not _module_available("slowapi")
        or not _module_available("cryptography")
        or not _module_available("azure")
        or not _module_available("redis")
    ):
        return True
    if path_str.endswith("tests/e2e/test_user_journey.py") and not _module_available(
        "cryptography"
    ):
        return True
    if path_str.endswith(
        "tests/integration/test_orchestration_workflow_integration.py"
    ) and not _module_available("sqlalchemy.exc"):
        return True
    if path_str.endswith(
        "tests/integration/test_workflow_engine_runtime.py"
    ) and not _module_available("cryptography"):
        return True
    if path_str.endswith("tests/test_artifact_validation.py") and not _jsonschema_has_validator():
        return True
    if path_str.endswith("tests/test_schema_validation.py") and not _jsonschema_has_validator():
        return True
    return False


def pytest_addoption(parser):
    parser.addoption(
        "--fail-on-unexpected-skips",
        action="store_true",
        default=os.getenv("PYTEST_FAIL_ON_UNEXPECTED_SKIPS", "0") == "1",
        help="Fail the run when missing-dependency or unclassified skips are observed.",
    )


def pytest_configure(config):
    global _PYTEST_CONFIG
    _PYTEST_CONFIG = config
    config._ppm_skip_counts = collections.Counter()
    config._ppm_skip_examples = {}


def _extract_skip_reason(report: pytest.TestReport) -> str:
    longrepr = report.longrepr
    if isinstance(longrepr, tuple) and len(longrepr) == 3:
        return str(longrepr[2])
    return str(longrepr)


def _classify_skip_reason(reason: str) -> str:
    lowered = reason.lower()
    if any(pattern in lowered for pattern in _PLATFORM_SKIP_PATTERNS):
        return "intentional_platform"
    if any(pattern in lowered for pattern in _MISSING_DEPENDENCY_SKIP_PATTERNS):
        return "missing_dependency"
    return "unclassified"


def _record_skip(config: pytest.Config, reason: str) -> None:
    category = _classify_skip_reason(reason)
    config._ppm_skip_counts[category] += 1
    config._ppm_skip_examples.setdefault(category, reason)


def pytest_collectreport(report):
    if report.outcome != "skipped" or _PYTEST_CONFIG is None:
        return
    _record_skip(_PYTEST_CONFIG, str(report.longrepr))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "setup" or not report.skipped:
        return

    reason = _extract_skip_reason(report)
    _record_skip(item.config, reason)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    counts = config._ppm_skip_counts
    if not counts:
        return

    terminalreporter.section("Skip classification summary")
    for category in ("intentional_platform", "missing_dependency", "unclassified"):
        count = counts.get(category, 0)
        example = config._ppm_skip_examples.get(category)
        message = f"{category.replace('_', ' ').title()}: {count}"
        if example:
            message += f" (example: {example})"
        terminalreporter.line(message)


def pytest_sessionfinish(session, exitstatus):
    if not session.config.getoption("--fail-on-unexpected-skips"):
        return

    counts = session.config._ppm_skip_counts
    missing_dependency_skips = counts.get("missing_dependency", 0)
    unclassified_skips = counts.get("unclassified", 0)
    if missing_dependency_skips or unclassified_skips:
        session.exitstatus = 1


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

    class MockAzureOpenAI:
        def __init__(self):
            self.calls = []

        def chat_completions(self, prompt: str) -> dict:
            self.calls.append(prompt)
            return {"id": "mock-response", "choices": [{"message": {"content": "ok"}}]}

    return MockAzureOpenAI()


@pytest.fixture
def mock_database():
    """Mock database connection for testing."""

    class MockDatabase:
        def __init__(self):
            self.queries = []

        def execute(self, query: str, params: dict | None = None) -> list[dict]:
            self.queries.append({"query": query, "params": params or {}})
            return []

    return MockDatabase()


@pytest.fixture
def mock_redis():
    """Mock Redis connection for testing."""

    class MockRedis:
        def __init__(self):
            self.store = {}

        def get(self, key: str):
            return self.store.get(key)

        def set(self, key: str, value: str):
            self.store[key] = value
            return True

    return MockRedis()


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
