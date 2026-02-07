"""Core agent execution logic shared by CLI wrappers."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
from typing import Any, cast

from agents.runtime import BaseAgent


def _load_module_from_path(path: Path):
    spec = importlib.util.spec_from_file_location("agent_module", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load agent module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resolve_agent_class(module, class_name: str | None) -> type[BaseAgent]:
    candidates = [
        obj
        for obj in module.__dict__.values()
        if inspect.isclass(obj) and issubclass(obj, BaseAgent) and obj is not BaseAgent
    ]
    if class_name:
        for candidate in candidates:
            if candidate.__name__ == class_name:
                return candidate
        raise LookupError(f"Agent class {class_name} not found in module.")
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise LookupError("No BaseAgent subclass found in module.")
    names = ", ".join(sorted(cls.__name__ for cls in candidates))
    raise LookupError(f"Multiple agent classes found ({names}). Provide --agent-class.")


async def _run_agent(agent: BaseAgent, input_payload: dict[str, Any] | None) -> None:
    if input_payload:
        result = await agent.execute(input_payload)
        print(json.dumps(result, indent=2))
        return

    await agent.initialize()
    summary = {
        "agent_id": agent.agent_id,
        "capabilities": agent.get_capabilities(),
        "config_keys": sorted(agent.config.keys()),
    }
    print(json.dumps(summary, indent=2))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a single PPM agent for local validation.")
    parser.add_argument("--agent-path", help="Path to the agent Python file.")
    parser.add_argument("--agent-module", help="Import path to the agent module.")
    parser.add_argument("--agent-class", help="Class name of the agent to instantiate.")
    parser.add_argument("--agent-id", help="Optional agent id override.")
    parser.add_argument("--input", help="JSON payload to pass to agent.execute().")
    return parser.parse_args()


def _load_config() -> dict[str, Any]:
    raw = os.getenv("AGENT_CONFIG_JSON", "").strip()
    if not raw:
        return {}
    return cast(dict[str, Any], json.loads(raw))


def main() -> None:
    args = _parse_args()

    agent_path = args.agent_path or os.getenv("AGENT_PATH")
    agent_module = args.agent_module or os.getenv("AGENT_MODULE")
    agent_class = args.agent_class or os.getenv("AGENT_CLASS")
    agent_id = args.agent_id or os.getenv("AGENT_ID")

    if not agent_path and not agent_module:
        raise SystemExit("Provide --agent-path or --agent-module to run an agent.")

    if agent_path:
        module = _load_module_from_path(Path(agent_path))
    else:
        assert agent_module
        module = importlib.import_module(agent_module)

    agent_cls = _resolve_agent_class(module, agent_class)
    config = _load_config()
    agent = agent_cls(agent_id=agent_id or agent_cls.__name__.lower(), config=config)

    input_payload = args.input or os.getenv("AGENT_INPUT")
    payload = json.loads(input_payload) if input_payload else None
    asyncio.run(_run_agent(agent, payload))


if __name__ == "__main__":
    main()
