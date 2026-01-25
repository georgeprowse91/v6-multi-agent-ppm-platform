from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..store import Store
from .stubs import route_intent as _route_intent, orchestrate as _orchestrate, run_domain_agent


def _prototype_data_dir() -> Path:
    # apps/web/ppm/agents/registry.py -> apps/web/data
    return Path(__file__).resolve().parents[2] / "data"


def list_agents() -> List[Dict[str, Any]]:
    """List agent metadata (from generated JSON) for UI display."""
    agents_file = _prototype_data_dir() / "agents.json"
    if not agents_file.exists():
        # Fallback: minimal list
        return [{"id": i, "title": f"Agent {i}"} for i in range(1, 26)]
    payload = json.loads(agents_file.read_text(encoding="utf-8"))
    return payload.get("agents", [])


def route_intent(query: str) -> Dict[str, Any]:
    return _route_intent(query)


def orchestrate(store: Store, *, actor: str, query: str, focus_entity_id: str | None = None) -> Dict[str, Any]:
    return _orchestrate(store, actor=actor, query=query, focus_entity_id=focus_entity_id)


def run_agent(store: Store, *, agent_id: int, actor: str, entity_id: str | None, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Run an agent stub (prototype) and record the run."""
    return run_domain_agent(store, agent_id=agent_id, actor=actor, entity_id=entity_id, inputs=inputs)
