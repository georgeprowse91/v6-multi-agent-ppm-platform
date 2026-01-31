from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from runtime import AgentRuntime  # noqa: E402


@pytest.mark.anyio
async def test_event_bus_executes_requested_agent(tmp_path: Path) -> None:
    runtime = AgentRuntime(data_dir=tmp_path)

    await runtime.event_bus.publish(
        "agent.requested",
        {"agent_id": "demand-intake", "payload": {"action": "get_pipeline"}},
    )

    completed_events = runtime.event_bus.get_recent_events("agent.completed")
    assert any(event.payload["agent_id"] == "demand-intake" for event in completed_events)
