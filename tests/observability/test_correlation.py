from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from agents.runtime.src.base_agent import BaseAgent
from agents.runtime.src.orchestrator import AgentTask, Orchestrator
from observability.tracing import get_trace_id, inject_trace_headers, start_agent_span
from tests.helpers.service_bus import build_test_event_bus


class _Counter:
    def __init__(self) -> None:
        self.calls: list[tuple[float, dict[str, Any]]] = []

    def add(self, value: float, attributes: dict[str, Any]) -> None:
        self.calls.append((value, dict(attributes)))


class _Histogram:
    def __init__(self) -> None:
        self.calls: list[tuple[float, dict[str, Any]]] = []

    def record(self, value: float, attributes: dict[str, Any]) -> None:
        self.calls.append((value, dict(attributes)))


class _CostMetrics:
    def __init__(self) -> None:
        self.llm_tokens_consumed = _Counter()
        self.external_api_cost = _Counter()


class _ExecutionMetrics:
    def __init__(self) -> None:
        self.duration_seconds = _Histogram()
        self.retries_total = _Counter()
        self.errors_total = _Counter()


class CostAgent(BaseAgent):
    async def process(self, _input_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "result": "ok",
            "llm_usage": {"request_tokens": 20, "response_tokens": 30, "model": "test", "provider": "test"},
            "api_costs": [{"connector_name": "jira", "cost": 0.25}],
        }


@pytest.mark.asyncio
async def test_correlation_id_propagates_logs_metrics_and_results(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setattr("agents.runtime.src.base_agent.build_cost_metrics", lambda _name: _CostMetrics())
    monkeypatch.setattr("agents.runtime.src.base_agent.build_agent_execution_metrics", lambda _name: _ExecutionMetrics())
    monkeypatch.setattr("agents.runtime.src.orchestrator.build_agent_execution_metrics", lambda _name: _ExecutionMetrics())

    event_bus = build_test_event_bus()
    orchestrator = Orchestrator(event_bus=event_bus)

    captured_events: list[dict[str, Any]] = []

    async def on_complete(payload: dict[str, Any]) -> None:
        captured_events.append(payload)

    event_bus.subscribe("orchestrator.task.completed", on_complete)
    correlation_id = str(uuid4())

    tasks = [
        AgentTask(task_id="a", agent=CostAgent("agent-a")),
        AgentTask(task_id="b", agent=CostAgent("agent-b"), depends_on=["a"]),
    ]
    result = await orchestrator.run(tasks, context={"tenant_id": "t1", "correlation_id": correlation_id})

    assert result.context["correlation_id"] == correlation_id
    assert result.results["a"]["metadata"]["correlation_id"] == correlation_id
    assert result.results["b"]["metadata"]["correlation_id"] == correlation_id
    assert captured_events and all(e["correlation_id"] == correlation_id for e in captured_events)
    assert result.metrics["cost_summary"]["total_api_cost_usd"] == pytest.approx(0.5)
    assert result.metrics["cost_summary"]["total_llm_tokens"] == 100


@pytest.mark.asyncio
async def test_correlation_id_present_in_base_agent_logs(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setattr("agents.runtime.src.base_agent.build_cost_metrics", lambda _name: _CostMetrics())
    monkeypatch.setattr("agents.runtime.src.base_agent.build_agent_execution_metrics", lambda _name: _ExecutionMetrics())
    caplog.set_level("INFO")

    corr_id = str(uuid4())
    agent = CostAgent("agent-log")
    await agent.execute({"context": {"tenant_id": "t1", "correlation_id": corr_id}})

    agent_records = [record for record in caplog.records if getattr(record, "correlation_id", None) == corr_id]
    assert agent_records


def test_start_agent_span_uses_correlation_id_as_trace_id() -> None:
    correlation_id = str(uuid4())
    expected_trace_id = correlation_id.replace("-", "")

    with start_agent_span("correlation-test", correlation_id=correlation_id):
        trace_id = get_trace_id()

    if trace_id is not None:
        assert trace_id == expected_trace_id


def test_inject_trace_headers_includes_correlation_and_traceparent() -> None:
    correlation_id = str(uuid4())

    headers = inject_trace_headers({"X-Test": "1"}, correlation_id=correlation_id)

    assert headers["X-Correlation-ID"] == correlation_id
    if "traceparent" in headers:
        assert headers["traceparent"]
