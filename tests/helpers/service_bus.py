from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from event_bus import ServiceBusEventBus


@dataclass
class MockServiceBusMessage:
    body: str


class _MockSender:
    def __init__(self, sent: list[MockServiceBusMessage]) -> None:
        self._sent = sent

    async def __aenter__(self) -> "_MockSender":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def send_messages(self, message: MockServiceBusMessage) -> None:
        self._sent.append(message)


class MockServiceBusClient:
    def __init__(self) -> None:
        self.sent: list[MockServiceBusMessage] = []

    async def __aenter__(self) -> "MockServiceBusClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    def get_topic_sender(self, topic_name: str) -> _MockSender:
        return _MockSender(self.sent)


def build_test_event_bus() -> ServiceBusEventBus:
    return ServiceBusEventBus(
        connection_string="Endpoint=sb://local/;SharedAccessKeyName=local;SharedAccessKey=local",
        client=MockServiceBusClient(),
        message_cls=MockServiceBusMessage,
        local_dispatch=True,
    )
