from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from azure.servicebus import ServiceBusClient, ServiceBusMessage

IOT_CONNECTORS = {"iot"}


class QueueClient:
    def send(self, payload: dict[str, Any]) -> None:
        raise NotImplementedError


@dataclass
class ServiceBusQueueClient(QueueClient):
    connection_string: str
    queue_name: str

    def send(self, payload: dict[str, Any]) -> None:
        client = ServiceBusClient.from_connection_string(self.connection_string)
        with client:
            sender = client.get_queue_sender(queue_name=self.queue_name)
            with sender:
                sender.send_messages(ServiceBusMessage(json.dumps(payload)))


class InMemoryQueueClient(QueueClient):
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    def send(self, payload: dict[str, Any]) -> None:
        self.messages.append(payload)


def build_sync_payload(
    *,
    job_id: str,
    connector: str | None,
    dry_run: bool,
    rules: list[str],
    sensor_data: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload = {
        "job_id": job_id,
        "connector": connector,
        "dry_run": dry_run,
        "rules": rules,
    }
    if connector in IOT_CONNECTORS:
        payload["sensor_data"] = sensor_data or []
        payload["event_type"] = "sensor_ingest"
    return payload


def enqueue_sync_job(
    queue_client: QueueClient,
    *,
    job_id: str,
    connector: str | None,
    dry_run: bool,
    rules: list[str],
    sensor_data: list[dict[str, Any]] | None = None,
) -> None:
    payload = build_sync_payload(
        job_id=job_id,
        connector=connector,
        dry_run=dry_run,
        rules=rules,
        sensor_data=sensor_data,
    )
    queue_client.send(payload)


def get_queue_client() -> QueueClient:
    connection = os.getenv("SERVICE_BUS_CONNECTION_STRING")
    queue_name = os.getenv("SERVICE_BUS_QUEUE", "data-sync")
    if connection:
        return ServiceBusQueueClient(connection, queue_name)
    return InMemoryQueueClient()
