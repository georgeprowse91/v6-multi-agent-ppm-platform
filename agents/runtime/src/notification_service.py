from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger("agents.runtime.notification_service")


@dataclass
class NotificationServiceClient:
    base_url: str
    client: httpx.AsyncClient
    auth_token: str | None = None

    @classmethod
    def from_url(
        cls,
        base_url: str,
        auth_token: str | None = None,
        **kwargs: Any,
    ) -> NotificationServiceClient:
        client = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=5.0, **kwargs)
        return cls(base_url=base_url.rstrip("/"), client=client, auth_token=auth_token)

    async def send_notification(
        self,
        *,
        tenant_id: str,
        template: str,
        variables: dict[str, Any],
        channel: str = "stdout",
        recipient: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "template": template,
            "variables": variables,
            "channel": channel,
            "recipient": recipient,
        }
        response = await self.client.post(
            "/v1/notifications/send",
            json=payload,
            headers=self._headers(tenant_id),
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self.client.aclose()

    def _headers(self, tenant_id: str) -> dict[str, str]:
        headers = {"X-Tenant-ID": tenant_id}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
