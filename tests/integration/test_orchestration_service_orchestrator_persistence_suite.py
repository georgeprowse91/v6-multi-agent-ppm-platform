from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

SERVICE_SRC = Path(__file__).resolve().parents[2] / "apps" / "orchestration-service" / "src"
if str(SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(SERVICE_SRC))

import types

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
    "orchestration_service_persistence_suite", SERVICE_SRC / "persistence.py"
)
sys.modules["persistence"] = persistence_module
orchestrator_module = _load_module(
    "orchestration_service_orchestrator_suite", SERVICE_SRC / "orchestrator.py"
)

AgentOrchestrator = orchestrator_module.AgentOrchestrator
WorkflowState = persistence_module.WorkflowState
JsonOrchestrationStateStore = persistence_module.JsonOrchestrationStateStore
OptimisticLockError = persistence_module.OptimisticLockError


class StubAgent:
    def __init__(self, agent_id: str, response: dict[str, Any]) -> None:
        self.agent_id = agent_id
        self.catalog_id = agent_id
        self.name = agent_id
        self._response = response

    async def execute(self, _: dict[str, Any]) -> dict[str, Any]:
        return self._response


class FakeHttpClient:
    def __init__(self, decision: str = "allow") -> None:
        self.calls: list[dict[str, Any]] = []
        self.decision = decision

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None

    async def post(self, url: str, json: dict[str, Any], headers: dict[str, str]):
        self.calls.append({"url": url, "json": json, "headers": headers})

        class _Response:
            def __init__(self, decision: str) -> None:
                self._decision = decision

            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, str]:
                return {"decision": self._decision}

        return _Response(self.decision)


@pytest.mark.asyncio
async def test_orchestrator_routes_query_and_dependency_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    orchestrator = AgentOrchestrator()
    orchestrator.initialized = True
    orchestrator.agents = {"agent-b": SimpleNamespace(), "agent-a": SimpleNamespace()}

    intent_response = {
        "success": True,
        "data": {
            "routing": [{"agent_id": "agent-a", "action": "summarize"}],
            "parameters": {"foo": "bar"},
        },
        "metadata": {
            "agent_id": "intent-router",
            "catalog_id": "intent-router",
            "timestamp": "2024-01-01T00:00:00Z",
            "correlation_id": "corr-1",
            "trace_id": None,
            "execution_time_seconds": 0.1,
            "policy_reasons": None,
        },
    }
    response_payload = {
        "success": True,
        "data": {"answer": "ok"},
        "metadata": {
            "agent_id": "response-orchestrator",
            "catalog_id": "response-orchestrator",
            "timestamp": "2024-01-01T00:00:00Z",
            "correlation_id": "corr-1",
            "trace_id": None,
            "execution_time_seconds": 0.2,
            "policy_reasons": None,
        },
    }

    orchestrator.intent_router = StubAgent("intent-router", intent_response)
    orchestrator.response_orchestrator = StubAgent("response-orchestrator", response_payload)

    routed = await orchestrator.process_query(
        "hello", context={"tenant_id": "t-1", "correlation_id": "corr-1"}
    )
    assert routed["success"] is True

    monkeypatch.setenv("DEMO_MODE", "1")
    monkeypatch.setenv("DEMO_MODE_FULL_RUN", "1")
    demo = await orchestrator.process_query("full platform demo", context={"tenant_id": "t-1"})
    assert demo["success"] is True

    orchestrator.register_dependency("agent-a", ["agent-b"])
    assert orchestrator.dependencies_satisfied("agent-a") is False
    orchestrator.set_agent_state("agent-b", "running")
    assert orchestrator.dependencies_satisfied("agent-a") is True


@pytest.mark.asyncio
async def test_policy_fallback_and_denial(monkeypatch: pytest.MonkeyPatch) -> None:
    orchestrator = AgentOrchestrator()

    monkeypatch.delenv("POLICY_ENGINE_URL", raising=False)
    await orchestrator.enforce_policy("tenant-1", "agent-x", ["viewer"])

    monkeypatch.setenv("POLICY_ENGINE_URL", "https://policy.local")
    monkeypatch.delenv("POLICY_ENGINE_SERVICE_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="token missing"):
        await orchestrator.enforce_policy("tenant-1", "agent-x", ["viewer"])

    deny_client = FakeHttpClient(decision="deny")
    monkeypatch.setenv("POLICY_ENGINE_SERVICE_TOKEN", "token")
    monkeypatch.setattr(orchestrator_module.httpx, "AsyncClient", lambda timeout: deny_client)
    with pytest.raises(PermissionError, match="Policy denied"):
        await orchestrator.enforce_policy("tenant-1", "agent-x", ["viewer"])
    assert deny_client.calls[0]["json"]["permission"] == "agent.execute.agent-x"


@pytest.mark.asyncio
async def test_persistence_roundtrip_and_restart_resume_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_file = tmp_path / "state.json"
    store = JsonOrchestrationStateStore(state_file)

    saved = await store.save(
        WorkflowState(
            run_id="run-1",
            tenant_id="tenant-1",
            status="running",
            last_checkpoint="step-1",
            payload={"nested": {"values": [1, 2]}},
        )
    )
    assert saved.version == 1

    loaded = await JsonOrchestrationStateStore(state_file).load("tenant-1")
    assert loaded["tenant-1:run-1"].payload == {"nested": {"values": [1, 2]}}

    monkeypatch.setenv("ORCHESTRATION_STATE_PATH", str(state_file))
    orch_a = AgentOrchestrator()
    await orch_a.persist_workflow_state(
        "tenant-1", "run-2", "paused", "step-2", {"tenant_id": "tenant-1"}
    )

    orch_b = AgentOrchestrator()
    orch_b.workflow_states = await orch_b.state_store.load()
    assert "run-2" in orch_b.resume_workflows("tenant-1")


def test_persistence_backend_selection_and_url_conversion(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ORCHESTRATION_STATE_BACKEND", "json")
    file_store = persistence_module.build_state_store(tmp_path / "state.json")
    assert isinstance(file_store, JsonOrchestrationStateStore)

    monkeypatch.setenv("ORCHESTRATION_STATE_BACKEND", "db")
    monkeypatch.setenv("ORCHESTRATION_DATABASE_URL", "postgresql://user:pass@localhost/db")
    converted = persistence_module._to_async_database_url(os.environ["ORCHESTRATION_DATABASE_URL"])
    assert converted.startswith("postgresql+asyncpg://")
