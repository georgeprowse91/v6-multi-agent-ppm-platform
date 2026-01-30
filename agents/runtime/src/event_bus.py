"""In-memory event bus for agent-to-agent communication."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from threading import Event, Thread
from typing import Any, Deque
from uuid import uuid4

try:
    from azure.servicebus import ServiceBusClient, ServiceBusMessage
    from azure.servicebus.management import ServiceBusAdministrationClient
except ImportError:  # pragma: no cover - optional dependency
    ServiceBusClient = None
    ServiceBusMessage = None
    ServiceBusAdministrationClient = None

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


class ServiceBusEventBus:
    """Azure Service Bus topic-based event bus with fan-out subscriptions."""

    def __init__(
        self,
        *,
        connection_string: str,
        topic: str = "ppm-events",
        subscription_name: str | None = None,
        event_log_size: int = 200,
    ) -> None:
        if not ServiceBusClient or not ServiceBusAdministrationClient:
            raise RuntimeError("azure-servicebus is not installed")
        self._connection_string = connection_string
        self._topic = topic
        self._subscription = subscription_name or f"sub-{uuid4().hex[:8]}"
        self._client = ServiceBusClient.from_connection_string(connection_string)
        self._admin = ServiceBusAdministrationClient.from_connection_string(connection_string)
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._metrics: dict[str, int] = defaultdict(int)
        self._event_log: Deque[EventRecord] = deque(maxlen=event_log_size)
        self._stop = Event()
        self._listener: Thread | None = None
        self._ensure_topic()
        self._ensure_subscription()
        self._start_listener()

    def _ensure_topic(self) -> None:
        try:
            self._admin.get_topic(self._topic)
        except Exception:
            self._admin.create_topic(self._topic)

    def _ensure_subscription(self) -> None:
        try:
            self._admin.get_subscription(self._topic, self._subscription)
        except Exception:
            self._admin.create_subscription(self._topic, self._subscription)

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        self._subscribers[topic].append(handler)

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        self._metrics[topic] += 1
        self._event_log.append(
            EventRecord(topic=topic, payload=payload, published_at=datetime.utcnow().isoformat())
        )
        message = ServiceBusMessage(json.dumps({"topic": topic, "payload": payload}))
        with self._client:
            sender = self._client.get_topic_sender(self._topic)
            with sender:
                sender.send_messages(message)

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)

    def get_recent_events(self, topic: str | None = None) -> list[EventRecord]:
        if topic is None:
            return list(self._event_log)
        return [record for record in self._event_log if record.topic == topic]

    def _start_listener(self) -> None:
        if self._listener and self._listener.is_alive():
            return
        self._listener = Thread(target=self._listen_loop, daemon=True)
        self._listener.start()

    def _listen_loop(self) -> None:
        while not self._stop.is_set():
            with self._client:
                receiver = self._client.get_subscription_receiver(
                    self._topic, self._subscription, max_wait_time=2
                )
                with receiver:
                    for message in receiver:
                        try:
                            data = json.loads(str(message))
                            topic = data.get("topic")
                            payload = data.get("payload", {})
                            self._metrics[topic] += 1
                            self._event_log.append(
                                EventRecord(
                                    topic=topic,
                                    payload=payload,
                                    published_at=datetime.utcnow().isoformat(),
                                )
                            )
                            handlers = list(self._subscribers.get(topic, []))
                            if handlers:
                                asyncio.run(self._dispatch(handlers, payload))
                            receiver.complete_message(message)
                        except Exception:
                            receiver.abandon_message(message)

    async def _dispatch(self, handlers: list[EventHandler], payload: dict[str, Any]) -> None:
        async def _invoke(handler: EventHandler) -> None:
            result = handler(payload)
            if asyncio.iscoroutine(result):
                await result

        await asyncio.gather(*(_invoke(handler) for handler in handlers))

    def stop(self) -> None:
        self._stop.set()
        if self._listener and self._listener.is_alive():
            self._listener.join(timeout=2)
