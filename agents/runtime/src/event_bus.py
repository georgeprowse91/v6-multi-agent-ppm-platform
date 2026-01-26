"""In-memory event bus for agent-to-agent communication."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Awaitable, Callable


EventHandler = Callable[[dict[str, Any]], Awaitable[None] | None]


class InMemoryEventBus:
    """Lightweight async-friendly event bus for local orchestration workflows."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Subscribe a handler to a topic."""
        self._subscribers[topic].append(handler)

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish an event to all subscribers."""
        handlers = list(self._subscribers.get(topic, []))
        if not handlers:
            return

        async def _invoke(handler: EventHandler) -> None:
            result = handler(payload)
            if asyncio.iscoroutine(result):
                await result

        await asyncio.gather(*(_invoke(handler) for handler in handlers))
