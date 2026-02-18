from __future__ import annotations

from typing import Any

from orchestrator_proxy import OrchestratorProxyClient


class AssistantService:
    """Business logic for assistant endpoints."""

    def __init__(self, orchestrator: OrchestratorProxyClient) -> None:
        self._orchestrator = orchestrator

    async def send(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._orchestrator.send_query(
            query=payload.get("message", ""),
            context=payload.get("context", {}),
            headers={},
            prompt=payload.get("prompt"),
        )
        return response.json()
