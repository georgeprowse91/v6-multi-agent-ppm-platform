"""Minimal harness to demonstrate orchestrator timeout enforcement."""

from __future__ import annotations

import asyncio
import os

from agents.runtime.src.base_agent import BaseAgent
from agents.runtime.src.orchestrator import AgentTask, Orchestrator


class SlowAgent(BaseAgent):
    async def process(self, input_data: dict[str, object]) -> dict[str, str]:
        delay_seconds = float(input_data.get("delay_seconds", 1.0))
        await asyncio.sleep(delay_seconds)
        return {"status": "completed"}


async def main() -> None:
    os.environ.setdefault("AGENT_TIMEOUT_SECONDS", "0.1")
    agent = SlowAgent(agent_id="slow-agent")
    task = AgentTask(task_id="slow-task", agent=agent, input_data={"delay_seconds": 1.0})
    result = await Orchestrator().run([task])
    print(result.results)


if __name__ == "__main__":
    asyncio.run(main())
