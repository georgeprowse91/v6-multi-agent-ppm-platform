"""Event bus helpers for agent-to-agent communication."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Protocol

REPO_ROOT = Path(__file__).resolve().parents[3]
EVENT_BUS_PACKAGE = REPO_ROOT / "packages" / "event-bus" / "src" / "event_bus"

spec = importlib.util.spec_from_file_location(
    "_ppm_event_bus",
    EVENT_BUS_PACKAGE / "__init__.py",
    submodule_search_locations=[str(EVENT_BUS_PACKAGE)],
)
if spec is None or spec.loader is None:
    raise ImportError(f"Unable to load event_bus package from {EVENT_BUS_PACKAGE}")

_event_bus_module = importlib.util.module_from_spec(spec)
sys.modules.setdefault("_ppm_event_bus", _event_bus_module)
_original_event_bus = sys.modules.get("event_bus")
sys.modules["event_bus"] = _event_bus_module
spec.loader.exec_module(_event_bus_module)
if _original_event_bus is not None:
    sys.modules["event_bus"] = _original_event_bus

EventHandler = _event_bus_module.EventHandler
EventRecord = _event_bus_module.EventRecord
ServiceBusEventBus = _event_bus_module.ServiceBusEventBus
NullEventBus = _event_bus_module.NullEventBus
get_event_bus = _event_bus_module.get_event_bus


class _EventBusProtocol(Protocol):
    """Structural protocol for event bus implementations (used for type hints)."""

    def subscribe(self, topic: str, handler: EventHandler) -> None: ...

    async def publish(self, topic: str, payload: dict[str, Any]) -> None: ...

    def get_metrics(self) -> dict[str, int]: ...

    def get_recent_events(self, topic: str | None = None) -> list[EventRecord]: ...


# Concrete default implementation – can be instantiated directly in tests and
# local environments where no Azure Service Bus is available.
EventBus = NullEventBus


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
