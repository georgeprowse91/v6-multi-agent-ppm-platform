"""In-memory event bus for agent-to-agent communication."""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Deque

EventHandler = Callable[[dict[str, Any]], Awaitable[None] | None]


@dataclass(frozen=True)
class EventRecord:
    topic: str
    payload: dict[str, Any]
    published_at: str


class InMemoryEventBus:
    """Lightweight async-friendly event bus for local orchestration workflows."""

    def __init__(self, *, event_log_size: int = 200) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._metrics: dict[str, int] = defaultdict(int)
        self._event_log: Deque[EventRecord] = deque(maxlen=event_log_size)

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Subscribe a handler to a topic."""
        self._subscribers[topic].append(handler)

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish an event to all subscribers."""
        self._metrics[topic] += 1
        self._event_log.append(
            EventRecord(topic=topic, payload=payload, published_at=datetime.utcnow().isoformat())
        )
        handlers = list(self._subscribers.get(topic, []))
        if not handlers:
            return

        async def _invoke(handler: EventHandler) -> None:
            result = handler(payload)
            if asyncio.iscoroutine(result):
                await result

        await asyncio.gather(*(_invoke(handler) for handler in handlers))

    def get_metrics(self) -> dict[str, int]:
        """Return a snapshot of event publish counts per topic."""
        return dict(self._metrics)

    def get_recent_events(self, topic: str | None = None) -> list[EventRecord]:
        """Return recent events, optionally filtered by topic."""
        if topic is None:
            return list(self._event_log)
        return [record for record in self._event_log if record.topic == topic]
