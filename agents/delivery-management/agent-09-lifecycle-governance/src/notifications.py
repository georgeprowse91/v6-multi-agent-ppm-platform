"""Notification helpers for lifecycle governance decisions."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

Notifier = Callable[[dict[str, Any]], Awaitable[None] | None]


class NotificationService:
    def __init__(self, notifier: Notifier | None = None) -> None:
        self._notifier = notifier

    async def notify_gate_decision(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._notifier:
            return {"status": "skipped", "reason": "notifier_not_configured"}
        result = self._notifier(payload)
        if asyncio.iscoroutine(result):
            await result
        return {"status": "sent"}

    async def notify_project_initiated(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.notify_gate_decision(payload)
