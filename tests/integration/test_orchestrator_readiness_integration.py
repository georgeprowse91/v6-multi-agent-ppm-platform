from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from agents.runtime.src.base_agent import BaseAgent
from agents.runtime.src.models import AgentPayload, ReadinessReport

SERVICE_SRC = Path(__file__).resolve().parents[2] / "services" / "orchestration-service" / "src"
if str(SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(SERVICE_SRC))

if "observability" not in sys.modules:
    observability_pkg = types.ModuleType("observability")
    observability_pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules["observability"] = observability_pkg

if "observability.logging" not in sys.modules:
    obs_logging = types.ModuleType("observability.logging")
    obs_logging.configure_logging = lambda _service: None
    sys.modules["observability.logging"] = obs_logging
    sys.modules["observability"].logging = obs_logging

if "observability.metrics" not in sys.modules:
    obs_metrics = types.ModuleType("observability.metrics")

    class RequestMetricsMiddleware:  # pragma: no cover - test stub
        def __init__(self, app, service_name=None):
            self.app = app

        async def __call__(self, scope, receive, send):
            await self.app(scope, receive, send)

    class _MetricStub:
        def labels(self, *_: Any):
            return self

        def inc(self) -> None:
            return None

        def observe(self, _value: float) -> None:
            return None

    obs_metrics.RequestMetricsMiddleware = RequestMetricsMiddleware
    obs_metrics.configure_metrics = lambda _service: None
    obs_metrics.agent_request_count = _MetricStub()
    obs_metrics.agent_request_latency = _MetricStub()
    sys.modules["observability.metrics"] = obs_metrics
    sys.modules["observability"].metrics = obs_metrics

if "observability.tracing" not in sys.modules:
    obs_tracing = types.ModuleType("observability.tracing")

    class TraceMiddleware:  # pragma: no cover - test stub
        def __init__(self, app, service_name=None):
            self.app = app

        async def __call__(self, scope, receive, send):
            await self.app(scope, receive, send)

    obs_tracing.TraceMiddleware = TraceMiddleware
    obs_tracing.configure_tracing = lambda _service: None
    obs_tracing.inject_trace_headers = lambda headers, correlation_id=None: headers
    sys.modules["observability.tracing"] = obs_tracing
    sys.modules["observability"].tracing = obs_tracing

if "security.auth" not in sys.modules:
    security_auth = types.ModuleType("security.auth")

    class AuthTenantMiddleware:  # pragma: no cover - test stub
        def __init__(self, app, exempt_paths=None):
            self.app = app

        async def __call__(self, scope, receive, send):
            await self.app(scope, receive, send)

    security_auth.AuthTenantMiddleware = AuthTenantMiddleware
    sys.modules["security.auth"] = security_auth

if "security.headers" not in sys.modules:
    security_headers = types.ModuleType("security.headers")

    class SecurityHeadersMiddleware:  # pragma: no cover - test stub
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            await self.app(scope, receive, send)

    security_headers.SecurityHeadersMiddleware = SecurityHeadersMiddleware
    sys.modules["security.headers"] = security_headers

if "security.errors" not in sys.modules:
    security_errors = types.ModuleType("security.errors")
    security_errors.register_error_handlers = lambda _app: None
    sys.modules["security.errors"] = security_errors

if "structlog" not in sys.modules:
    structlog_mod = types.ModuleType("structlog")

    class _Bound:
        def info(self, *_: Any, **__: Any) -> None:
            return None

    structlog_mod.get_logger = lambda: types.SimpleNamespace(bind=lambda **kwargs: _Bound())
    sys.modules["structlog"] = structlog_mod


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


persistence_module = _load_module(
    "orchestration_service_persistence_readiness", SERVICE_SRC / "persistence.py"
)
sys.modules["persistence"] = persistence_module
orchestrator_module = _load_module(
    "orchestration_service_orchestrator_readiness", SERVICE_SRC / "orchestrator.py"
)
sys.modules["orchestrator"] = orchestrator_module

AgentOrchestrator = orchestrator_module.AgentOrchestrator


class ReadyTestAgent(BaseAgent):
    async def process(self, input_data: dict[str, Any]) -> AgentPayload:
        return AgentPayload(**{"ok": True, "input": input_data})


@pytest.mark.asyncio
async def test_readiness_happy_path_registers_running_agent() -> None:
    orchestrator = AgentOrchestrator()
    agent = ReadyTestAgent(
        agent_id="agent-ready",
        config={
            "required_config_keys": ["api_key"],
            "api_key": "test-key",
            "required_schema_keys": ["request"],
            "schemas": {"request": {"type": "object"}},
        },
    )

    await orchestrator._initialize_and_register_agent(agent)

    assert orchestrator.get_agent("agent-ready") is agent
    assert orchestrator.get_agent_state("agent-ready").status == "running"
    readiness = orchestrator.get_agent_readiness("agent-ready")
    assert isinstance(readiness, ReadinessReport)
    assert readiness.ready is True


@pytest.mark.asyncio
async def test_readiness_failure_quarantines_agent() -> None:
    orchestrator = AgentOrchestrator()
    agent = ReadyTestAgent(
        agent_id="agent-bad",
        config={
            "required_config_keys": ["api_key"],
            "required_schema_keys": ["request"],
            "schemas": {},
        },
    )

    await orchestrator._initialize_and_register_agent(agent)

    assert orchestrator.get_agent("agent-bad") is None
    state = orchestrator.get_agent_state("agent-bad")
    assert state is not None
    assert state.status == "quarantined"
    readiness = orchestrator.get_agent_readiness("agent-bad")
    assert readiness is not None
    assert readiness.ready is False
    assert "Missing required configuration keys" in (readiness.last_failure_reason or "")
