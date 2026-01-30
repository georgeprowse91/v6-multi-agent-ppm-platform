from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class WorkflowTaskMessage:
    message_id: str
    tenant_id: str
    instance_id: str
    task_id: str
    task_type: str | None = None
    payload: dict[str, Any] | None = None


class WorkflowTaskQueue(Protocol):
    async def publish_task(self, message: WorkflowTaskMessage) -> None:
        ...

    async def reserve_task(self) -> WorkflowTaskMessage | None:
        ...

    async def ack_task(self, message_id: str) -> None:
        ...

    async def fail_task(self, message_id: str, reason: str | None = None) -> None:
        ...


class InMemoryWorkflowTaskQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[WorkflowTaskMessage] = asyncio.Queue()
        self._in_flight: dict[str, WorkflowTaskMessage] = {}
        self.failed: dict[str, str | None] = {}

    async def publish_task(self, message: WorkflowTaskMessage) -> None:
        await self._queue.put(message)

    async def reserve_task(self) -> WorkflowTaskMessage | None:
        try:
            message = self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None
        self._in_flight[message.message_id] = message
        return message

    async def ack_task(self, message_id: str) -> None:
        self._in_flight.pop(message_id, None)

    async def fail_task(self, message_id: str, reason: str | None = None) -> None:
        message = self._in_flight.pop(message_id, None)
        if message:
            self.failed[message_id] = reason


class RabbitMQWorkflowTaskQueue:
    def __init__(self, amqp_url: str, queue_name: str = "workflow.tasks") -> None:
        import aio_pika

        self._amqp_url = amqp_url
        self._queue_name = queue_name
        self._connection = None
        self._channel = None
        self._queue = None
        self._aio_pika = aio_pika

    async def _ensure_connection(self) -> None:
        if self._connection:
            return
        self._connection = await self._aio_pika.connect_robust(self._amqp_url)
        self._channel = await self._connection.channel()
        self._queue = await self._channel.declare_queue(self._queue_name, durable=True)

    async def publish_task(self, message: WorkflowTaskMessage) -> None:
        await self._ensure_connection()
        body = self._aio_pika.Message(
            body=_serialize_message(message),
            delivery_mode=self._aio_pika.DeliveryMode.PERSISTENT,
        )
        await self._channel.default_exchange.publish(body, routing_key=self._queue_name)

    async def reserve_task(self) -> WorkflowTaskMessage | None:
        await self._ensure_connection()
        if not self._queue:
            return None
        incoming = await self._queue.get(no_ack=False, fail=False)
        if not incoming:
            return None
        payload = _deserialize_message(incoming.body)
        message = WorkflowTaskMessage(**payload)
        self._in_flight_message = incoming
        return message

    async def ack_task(self, message_id: str) -> None:
        if hasattr(self, "_in_flight_message"):
            await self._in_flight_message.ack()
            delattr(self, "_in_flight_message")

    async def fail_task(self, message_id: str, reason: str | None = None) -> None:
        if hasattr(self, "_in_flight_message"):
            await self._in_flight_message.nack(requeue=True)
            delattr(self, "_in_flight_message")


class NoopWorkflowTaskQueue:
    async def publish_task(self, message: WorkflowTaskMessage) -> None:
        return None

    async def reserve_task(self) -> WorkflowTaskMessage | None:
        return None

    async def ack_task(self, message_id: str) -> None:
        return None

    async def fail_task(self, message_id: str, reason: str | None = None) -> None:
        return None


def build_task_queue(config: dict[str, Any] | None = None) -> WorkflowTaskQueue:
    config = config or {}
    backend = (config.get("workflow_queue_backend") or "").lower()
    amqp_url = config.get("workflow_queue_url")
    if backend in {"rabbitmq", "amqp"}:
        if not amqp_url:
            raise ValueError("workflow_queue_url is required for RabbitMQ backend")
        return RabbitMQWorkflowTaskQueue(amqp_url)
    if backend in {"noop", "disabled"}:
        return NoopWorkflowTaskQueue()
    return InMemoryWorkflowTaskQueue()


def build_task_message(
    *, tenant_id: str, instance_id: str, task_id: str, task_type: str | None, payload: dict[str, Any]
) -> WorkflowTaskMessage:
    return WorkflowTaskMessage(
        message_id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        instance_id=instance_id,
        task_id=task_id,
        task_type=task_type,
        payload=payload,
    )


def _serialize_message(message: WorkflowTaskMessage) -> bytes:
    import json

    return json.dumps(
        {
            "message_id": message.message_id,
            "tenant_id": message.tenant_id,
            "instance_id": message.instance_id,
            "task_id": message.task_id,
            "task_type": message.task_type,
            "payload": message.payload,
        }
    ).encode("utf-8")


def _deserialize_message(payload: bytes) -> dict[str, Any]:
    import json

    return json.loads(payload.decode("utf-8"))
