from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

EVENT_BUS_SRC = Path(__file__).resolve().parents[2] / "packages" / "event_bus" / "src"
if str(EVENT_BUS_SRC) not in sys.path:
    sys.path.insert(0, str(EVENT_BUS_SRC))

from event_bus import ServiceBusEventBus  # noqa: E402


class FakeReceivedMessage:
    def __init__(self, body: bytes) -> None:
        self.body = [body]


class FakeReceiver:
    def __init__(self, messages: list[FakeReceivedMessage]) -> None:
        self._messages = list(messages)
        self.completed: list[FakeReceivedMessage] = []
        self.abandoned: list[FakeReceivedMessage] = []

    async def __aenter__(self) -> "FakeReceiver":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def __aiter__(self):
        async def _iterator():
            while self._messages:
                yield self._messages.pop(0)

        return _iterator()

    async def complete_message(self, message: FakeReceivedMessage) -> None:
        self.completed.append(message)

    async def abandon_message(self, message: FakeReceivedMessage) -> None:
        self.abandoned.append(message)


class FakeSender:
    async def __aenter__(self) -> "FakeSender":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FakeServiceBusMessage:
    def __init__(self, body: str) -> None:
        self.body = body


class FakeClient:
    def __init__(self, receiver: FakeReceiver) -> None:
        self.receiver = receiver
        self.sender = FakeSender()
        self.closed = False

    async def __aenter__(self) -> "FakeClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def get_subscription_receiver(self, *args, **kwargs) -> FakeReceiver:
        return self.receiver

    def get_topic_sender(self, *args, **kwargs) -> FakeSender:
        return self.sender

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_service_bus_event_bus_receives_messages() -> None:
    handled = asyncio.Event()
    received: dict[str, str] = {}

    async def handler(payload: dict[str, str]) -> None:
        received.update(payload)
        handled.set()

    message_body = json.dumps({"topic": "agent.requested", "payload": {"value": "ok"}})
    receiver = FakeReceiver([FakeReceivedMessage(message_body.encode("utf-8"))])
    client = FakeClient(receiver)
    bus = ServiceBusEventBus(
        connection_string="Endpoint=sb://example/;SharedAccessKeyName=key;SharedAccessKey=abc",
        topic_name="ppm-events",
        subscription_name="sub-1",
        client=client,
        message_cls=FakeServiceBusMessage,
        receiver_max_wait_time=0,
    )
    bus.subscribe("agent.requested", handler)

    await bus.start()
    await asyncio.wait_for(handled.wait(), timeout=1)
    await bus.stop()

    assert received["value"] == "ok"
    assert bus.get_metrics()["agent.requested"] == 1
    assert receiver.completed
