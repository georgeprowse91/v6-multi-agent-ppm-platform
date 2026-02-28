from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from agents.runtime.src.base_agent import BaseAgent
from agents.runtime.src.orchestrator import AgentTask, Orchestrator
from tests.helpers.service_bus import build_test_event_bus

REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_PATH = REPO_ROOT / "connectors" / "sdk" / "src"
SDK_PATH_STR = str(SDK_PATH.resolve())
if SDK_PATH_STR not in sys.path:
    sys.path.insert(0, SDK_PATH_STR)

from base_connector import BaseConnector, ConnectorCategory, ConnectorConfig  # noqa: E402


class _Counter:
    def __init__(self) -> None:
        self.total = 0.0

    def add(self, value: float, _attributes: dict[str, Any]) -> None:
        self.total += value


class _CostMetrics:
    def __init__(self) -> None:
        self.llm_tokens_consumed = _Counter()
        self.external_api_cost = _Counter()


class CostAwareAgent(BaseAgent):
    async def process(self, _input_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "result": "ok",
            "llm_usage": {
                "request_tokens": 120,
                "response_tokens": 45,
                "model": "gpt-4o-mini",
                "provider": "openai",
            },
            "api_costs": [
                {"connector_name": "jira", "cost": 0.12},
                {"connector_name": "servicenow", "cost": 0.35},
            ],
        }


@pytest.mark.asyncio
async def test_base_agent_records_cost_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "agents.runtime.src.base_agent.build_cost_metrics", lambda _name: _CostMetrics()
    )
    agent = CostAwareAgent(agent_id="cost-agent")

    result = await agent.execute({"context": {"correlation_id": "cost-1"}})
    metadata = result["metadata"]

    assert metadata["cost_summary"]["llm_tokens"]["total"] == 165
    assert metadata["cost_summary"]["api_cost_total_usd"] == pytest.approx(0.47)
    assert metadata["cost_summary"]["api_cost_by_connector"]["jira"] == pytest.approx(0.12)


@pytest.mark.asyncio
async def test_orchestrator_aggregates_cost_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "agents.runtime.src.base_agent.build_cost_metrics", lambda _name: _CostMetrics()
    )
    orchestrator = Orchestrator(event_bus=build_test_event_bus())

    tasks = [AgentTask(task_id="cost-task", agent=CostAwareAgent("agent-1"))]
    result = await orchestrator.run(tasks, context={"correlation_id": "corr-1"})

    assert result.metrics["cost_summary"]["total_api_cost_usd"] == pytest.approx(0.47)
    assert result.metrics["cost_summary"]["total_llm_tokens"] == 165
    assert result.context["cost_summary"]["per_agent"]["cost-task"][
        "api_cost_total_usd"
    ] == pytest.approx(0.47)


class DummyConnector(BaseConnector):
    CONNECTOR_ID = "dummy"

    def authenticate(self) -> bool:
        return True

    def test_connection(self):
        raise NotImplementedError

    def read(self, resource_type: str, filters=None, limit: int = 100, offset: int = 0):
        return []

    def _execute_call(
        self, endpoint: str, payload: dict[str, Any], *, timeout: float
    ) -> dict[str, Any]:
        return {"usage": {"model": "gpt-4o-mini", "prompt_tokens": 1000, "completion_tokens": 500}}


def test_connector_estimates_call_cost_from_pricing() -> None:
    connector = DummyConnector(
        ConnectorConfig(connector_id="dummy", name="Dummy", category=ConnectorCategory.PM),
        max_retries=0,
    )

    connector.call("/chat", {"query": "hello"})

    # Includes only model token cost from ops/config/pricing.yaml defaults.
    assert connector.last_call_cost_usd == pytest.approx(0.00045)
