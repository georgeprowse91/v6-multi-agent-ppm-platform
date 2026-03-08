from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, cast

import httpx


@dataclass
class AgentClient:
    base_url: str
    timeout: float = 10.0
    token: str | None = None
    transport: httpx.AsyncBaseTransport | None = None

    async def execute(
        self,
        agent_id: str,
        action: str,
        payload: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request_payload = {
            "action": action,
            "payload": payload,
            "context": context or {},
        }
        async with httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout, transport=self.transport
        ) as client:
            response = await client.post(
                f"/agents/{agent_id}/execute", json=request_payload, headers=headers
            )
            response.raise_for_status()
            return cast(dict[str, Any], response.json())


def get_agent_client() -> AgentClient | None:
    base_url = os.getenv("AGENT_SERVICE_URL")
    if not base_url:
        return None
    token = os.getenv("AGENT_SERVICE_TOKEN")
    timeout = float(os.getenv("AGENT_SERVICE_TIMEOUT", "10"))
    return AgentClient(base_url=base_url.rstrip("/"), timeout=timeout, token=token)
