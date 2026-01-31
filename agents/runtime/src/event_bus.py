"""Event bus helpers for agent-to-agent communication."""

from __future__ import annotations

import asyncio
import sys
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

REPO_ROOT = Path(__file__).resolve().parents[3]
EVENT_BUS_SRC = REPO_ROOT / "packages" / "event_bus" / "src"
if EVENT_BUS_SRC.exists() and str(EVENT_BUS_SRC) not in sys.path:
    sys.path.insert(0, str(EVENT_BUS_SRC))

from event_bus import EventHandler, EventRecord, ServiceBusEventBus


class EventBus(Protocol):
    def subscribe(self, topic: str, handler: EventHandler) -> None:
        ...

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        ...

    def get_metrics(self) -> dict[str, int]:
        ...

    def get_recent_events(self, topic: str | None = None) -> list[EventRecord]:
        ...


class InMemoryEventBus:
    """Lightweight async-friendly event bus for local orchestration workflows."""

    def __init__(self, *, event_log_size: int = 200) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._metrics: dict[str, int] = defaultdict(int)
        self._event_log: deque[EventRecord] = deque(maxlen=event_log_size)

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
