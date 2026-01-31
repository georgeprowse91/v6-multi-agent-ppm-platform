from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

EVENT_BUS_SRC = Path(__file__).resolve().parents[2] / "packages" / "event_bus" / "src"
if str(EVENT_BUS_SRC) not in sys.path:
    sys.path.insert(0, str(EVENT_BUS_SRC))

from event_bus import ServiceBusEventBus  # noqa: E402


class FakeServiceBusMessage:
    def __init__(self, body: str) -> None:
        self.body = body


class FakeSender:
    def __init__(self) -> None:
        self.messages: list[FakeServiceBusMessage] = []

    async def __aenter__(self) -> "FakeSender":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def send_messages(self, message: FakeServiceBusMessage) -> None:
        self.messages.append(message)


class FakeClient:
    def __init__(self) -> None:
        self.sender = FakeSender()
        self.topic_name: str | None = None
        self.closed = False

    async def __aenter__(self) -> "FakeClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def get_topic_sender(self, topic_name: str) -> FakeSender:
        self.topic_name = topic_name
        return self.sender

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_service_bus_event_bus_publishes_messages() -> None:
    client = FakeClient()
    bus = ServiceBusEventBus(
        connection_string="Endpoint=sb://example/;SharedAccessKeyName=key;SharedAccessKey=abc",
        topic_name="ppm-events",
        client=client,
        message_cls=FakeServiceBusMessage,
    )

    await bus.publish("agent.started", {"agent_id": "agent-1"})

    assert client.sender.messages
    payload = json.loads(client.sender.messages[0].body)
    assert payload["topic"] == "agent.started"
    assert payload["payload"]["agent_id"] == "agent-1"
    assert bus.get_metrics()["agent.started"] == 1
    assert bus.get_recent_events("agent.started")[0].payload["agent_id"] == "agent-1"
