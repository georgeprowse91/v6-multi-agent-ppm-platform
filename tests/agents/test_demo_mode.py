from __future__ import annotations

import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = REPO_ROOT / "services" / "agent-runtime" / "src"
RUNTIME_PATH = RUNTIME_SRC / "runtime.py"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

spec = spec_from_file_location("agent_runtime_module", RUNTIME_PATH)
assert spec and spec.loader
module = module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
AgentRuntime = module.AgentRuntime


class InMemoryEventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Any]] = {}

    def subscribe(self, topic: str, handler: Any) -> None:
        self._subscribers.setdefault(topic, []).append(handler)

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        for handler in self._subscribers.get(topic, []):
            await handler(payload)

    def get_metrics(self) -> dict[str, int]:
        return {topic: len(handlers) for topic, handlers in self._subscribers.items()}

    def get_recent_events(self, topic: str | None = None) -> list[Any]:
        return []


@pytest.mark.asyncio
async def test_agents_use_scripted_fixtures_in_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "true")

    runtime = AgentRuntime(event_bus=InMemoryEventBus())
    specs = runtime._build_agent_specs()

    for spec in specs:
        fixture_path = spec.fixture_dir / "sample-response.json"
        fixture_payload = json.loads(fixture_path.read_text())
        expected = fixture_payload["scripted_response"]

        response = await runtime.execute_agent(spec.agent_id, {"action": "ignored_in_demo_mode"})

        assert response == expected


@pytest.mark.asyncio
async def test_agents_fall_back_to_normal_execution_when_demo_mode_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEMO_MODE", raising=False)

    original_build_specs = AgentRuntime._build_agent_specs

    def _intent_router_only(self: AgentRuntime):
        return [spec for spec in original_build_specs(self) if spec.agent_id == "intent-router-agent"]

    monkeypatch.setattr(AgentRuntime, "_build_agent_specs", _intent_router_only)

    runtime = AgentRuntime(event_bus=InMemoryEventBus())

    response = await runtime.execute_agent("intent-router-agent", {"query": "Need demand intake support"})

    assert response["success"] is True
    assert "routing" in response["data"]
    assert isinstance(response["data"]["routing"], list)
