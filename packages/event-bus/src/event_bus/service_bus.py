from __future__ import annotations

import asyncio
import json
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from event_bus.models import EventHandler, EventRecord

if TYPE_CHECKING:
    pass


class ServiceBusEventBus:
    """Azure Service Bus topic-backed event bus with async publishing and listening."""

    def __init__(
        self,
        *,
        connection_string: str,
        topic_name: str = "ppm-events",
        subscription_name: str | None = None,
        event_log_size: int = 200,
        receiver_max_wait_time: int = 2,
        client: Any | None = None,
        message_cls: type[Any] | None = None,
        local_dispatch: bool = False,
    ) -> None:
        if client is None or message_cls is None:
            from azure.servicebus import ServiceBusMessage
            from azure.servicebus.aio import ServiceBusClient

            if client is None:
                client = ServiceBusClient.from_connection_string(connection_string)
            if message_cls is None:
                message_cls = ServiceBusMessage
        self._connection_string = connection_string
        self._topic_name = topic_name
        self._subscription_name = subscription_name or f"sub-{uuid4().hex[:8]}"
        self._client = client
        self._message_cls = message_cls
        self._receiver_max_wait_time = receiver_max_wait_time
        self._local_dispatch = local_dispatch
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._metrics: dict[str, int] = defaultdict(int)
        self._event_log: deque[EventRecord] = deque(maxlen=event_log_size)
        self._stop_event = asyncio.Event()
        self._listen_task: asyncio.Task[None] | None = None

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        self._subscribers[topic].append(handler)

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        self._metrics[topic] += 1
        self._event_log.append(
            EventRecord(
                topic=topic, payload=payload, published_at=datetime.now(timezone.utc).isoformat()
            )
        )
        message = self._message_cls(json.dumps({"topic": topic, "payload": payload}))
        async with self._client:
            sender = self._client.get_topic_sender(self._topic_name)
            async with sender:
                await sender.send_messages(message)
        if self._local_dispatch:
            handlers = list(self._subscribers.get(topic, []))
            if handlers:
                await self._dispatch(handlers, payload)

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)

    def get_recent_events(self, topic: str | None = None) -> list[EventRecord]:
        if topic is None:
            return list(self._event_log)
        return [record for record in self._event_log if record.topic == topic]

    async def start(self) -> None:
        if self._listen_task and not self._listen_task.done():
            return
        self._stop_event = asyncio.Event()
        self._listen_task = asyncio.create_task(self._listen_loop())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        if hasattr(self._client, "close"):
            await self._client.close()

    async def _listen_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                async with self._client:
                    receiver = self._client.get_subscription_receiver(
                        self._topic_name,
                        self._subscription_name,
                        max_wait_time=self._receiver_max_wait_time,
                    )
                    async with receiver:
                        async for message in receiver:
                            await self._handle_message(receiver, message)
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                break

    async def _handle_message(self, receiver: Any, message: Any) -> None:
        try:
            payload = self._decode_message(message)
            topic = payload.get("topic")
            event_payload = payload.get("payload", {})
            if topic:
                self._metrics[topic] += 1
                self._event_log.append(
                    EventRecord(
                        topic=topic,
                        payload=event_payload,
                        published_at=datetime.now(timezone.utc).isoformat(),
                    )
                )
                handlers = list(self._subscribers.get(topic, []))
                if handlers:
                    await self._dispatch(handlers, event_payload)
            await receiver.complete_message(message)
        except Exception:
            await receiver.abandon_message(message)

    def _decode_message(self, message: Any) -> dict[str, Any]:
        body = message.body
        if isinstance(body, (bytes, bytearray)):
            raw = body
        else:
            raw = b"".join(body)
        return dict(json.loads(raw.decode("utf-8")))

    async def _dispatch(self, handlers: list[EventHandler], payload: dict[str, Any]) -> None:
        async def _invoke(handler: EventHandler) -> None:
            result = handler(payload)
            if asyncio.iscoroutine(result):
                await result

        await asyncio.gather(*(_invoke(handler) for handler in handlers))
