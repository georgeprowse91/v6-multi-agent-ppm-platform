"""Shared event bus implementations."""

from __future__ import annotations

import logging
import os
from typing import Any, Final

from event_bus.models import EventHandler, EventRecord
from event_bus.service_bus import ServiceBusEventBus

_DEFAULT_TOPIC: Final[str] = "ppm-events"
_EVENT_BUS: ServiceBusEventBus | NullEventBus | None = None

logger = logging.getLogger(__name__)


class NullEventBus:
    """No-op event bus used when no Azure Service Bus connection string is configured.

    Events are silently discarded; subscribe handlers are never called.  This
    allows agents and services to start without a real Service Bus in local
    development and test environments.
    """

    def subscribe(self, topic: str, handler: EventHandler) -> None:  # noqa: ARG002
        pass

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:  # noqa: ARG002
        pass

    def get_metrics(self) -> dict[str, int]:
        return {}

    def get_recent_events(self, topic: str | None = None) -> list[EventRecord]:  # noqa: ARG002
        return []

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


def get_event_bus() -> ServiceBusEventBus | NullEventBus:
    """Return a singleton event bus using environment configuration.

    When ``AZURE_SERVICE_BUS_CONNECTION_STRING`` (or ``SERVICE_BUS_CONNECTION_STRING``)
    is set, a real Azure Service Bus-backed bus is returned.  Otherwise a
    :class:`NullEventBus` is returned so that agents can start without an
    external dependency (e.g. in unit tests and local development).
    """
    global _EVENT_BUS
    if _EVENT_BUS is None:
        connection_string = os.getenv("AZURE_SERVICE_BUS_CONNECTION_STRING") or os.getenv(
            "SERVICE_BUS_CONNECTION_STRING"
        )
        if not connection_string:
            logger.warning(
                "AZURE_SERVICE_BUS_CONNECTION_STRING not set; using NullEventBus "
                "(events will be silently discarded)."
            )
            _EVENT_BUS = NullEventBus()
        else:
            topic_name = (
                os.getenv("SERVICE_BUS_QUEUE_NAME")
                or os.getenv("EVENT_BUS_TOPIC")
                or _DEFAULT_TOPIC
            )
            subscription_name = os.getenv("SERVICE_BUS_SUBSCRIPTION_NAME") or os.getenv(
                "EVENT_BUS_SUBSCRIPTION"
            )
            _EVENT_BUS = ServiceBusEventBus(
                connection_string=connection_string,
                topic_name=topic_name,
                subscription_name=subscription_name,
            )
    return _EVENT_BUS


__all__ = ["EventHandler", "EventRecord", "NullEventBus", "ServiceBusEventBus", "get_event_bus"]
