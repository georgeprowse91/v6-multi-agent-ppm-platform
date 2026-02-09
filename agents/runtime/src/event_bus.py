"""Event bus helpers for agent-to-agent communication."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Protocol

REPO_ROOT = Path(__file__).resolve().parents[3]
EVENT_BUS_SRC = REPO_ROOT / "packages" / "event_bus" / "src"
if EVENT_BUS_SRC.exists() and str(EVENT_BUS_SRC) not in sys.path:
    sys.path.insert(0, str(EVENT_BUS_SRC))

from event_bus import EventHandler, EventRecord, ServiceBusEventBus, get_event_bus


class EventBus(Protocol):
    def subscribe(self, topic: str, handler: EventHandler) -> None:
        ...

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        ...

    def get_metrics(self) -> dict[str, int]:
        ...

    def get_recent_events(self, topic: str | None = None) -> list[EventRecord]:
        ...


INSIGHT_TOPIC = "orchestrator.insights.shared"


def subscribe_to_insights(event_bus: EventBus, handler: EventHandler) -> None:
    event_bus.subscribe(INSIGHT_TOPIC, handler)


async def publish_insight(event_bus: EventBus, payload: dict[str, Any]) -> None:
    await event_bus.publish(INSIGHT_TOPIC, payload)


__all__ = [
    "EventBus",
    "EventHandler",
    "EventRecord",
    "INSIGHT_TOPIC",
    "ServiceBusEventBus",
    "get_event_bus",
    "publish_insight",
    "subscribe_to_insights",
]
