from __future__ import annotations

import json

import pytest


@pytest.mark.asyncio
async def test_orchestrator_loads_state(monkeypatch, tmp_path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps({"run-1": {"status": "running", "last_checkpoint": "step-1", "payload": {}}})
    )
    monkeypatch.setenv("ORCHESTRATION_STATE_PATH", str(state_path))

    from orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator()
    await orchestrator.initialize()

    assert "run-1" in orchestrator.resume_workflows()
