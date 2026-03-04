"""Event bus integration utilities."""

from __future__ import annotations

import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Common event types shared across agents."""

    SCHEDULE_CREATED = "schedule.created"
    SCHEDULE_UPDATED = "schedule.updated"
    RISK_CREATED = "risk.created"
    RESOURCE_ALLOCATED = "resource.allocated"
    QUALITY_METRIC_RECORDED = "quality.metric.recorded"
    COMPLIANCE_EVIDENCE_ADDED = "compliance.evidence.added"
    PROCESS_LOGGED = "process.logged"


class ScheduleEventData(BaseModel):
    schedule_id: str
    owner: Optional[str] = None
    status: Optional[str] = None


class RiskEventData(BaseModel):
    risk_id: str
    severity: str
    mitigation: Optional[str] = None


class ResourceEventData(BaseModel):
    resource_id: str
    allocation: float


class EventEnvelope(BaseModel):
    """Shared event schema used across the platform."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = Field(..., description="Event type, e.g. schedule.created")
    subject: str = Field(..., description="Entity subject identifier")
    source: str = Field(default="multi-agent-ppm", description="Event source")
    time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: Dict[str, Any] = Field(default_factory=dict)
    version: str = Field(default="1.0")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        return json.loads(self.model_dump_json())


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 0.5
    max_backoff_seconds: float = 5.0


class EventBusSettings(BaseSettings):
    """Configuration for event bus providers."""

    model_config = SettingsConfigDict(env_prefix="EVENT_BUS_", env_file=".env")

    provider: str = "in_memory"
    service_bus_connection_string: Optional[str] = None
    service_bus_topic: str = "ppm-events"
    service_bus_subscription: str = "ppm-subscription"
    event_grid_endpoint: Optional[str] = None
    event_grid_key: Optional[str] = None
    event_grid_topic: str = "ppm-events"
    kafka_bootstrap_servers: Optional[str] = None
    kafka_topic: str = "ppm-events"


class EventBusProvider(ABC):
    @abstractmethod
    def create_topic(self, name: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    @abstractmethod
    def create_queue(self, name: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    @abstractmethod
    def publish(self, topic: str, payload: Dict[str, Any]) -> None:  # pragma: no cover
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        raise NotImplementedError


class InMemoryEventBusProvider(EventBusProvider):
    """Simple in-memory provider for tests and local development."""

    def __init__(self) -> None:
        self._topics: Dict[str, Deque[Dict[str, Any]]] = defaultdict(deque)
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = defaultdict(list)

    def create_topic(self, name: str) -> None:
        self._topics.setdefault(name, deque())

    def create_queue(self, name: str) -> None:
        self._topics.setdefault(name, deque())

    def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        self._topics[topic].append(payload)
        for handler in self._subscribers.get(topic, []):
            handler(payload)

    def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        self._subscribers[topic].append(handler)

    def drain(self, topic: str) -> Iterable[Dict[str, Any]]:
        while self._topics[topic]:
            yield self._topics[topic].popleft()


class AzureServiceBusProvider(EventBusProvider):
    """Azure Service Bus provider implementation."""

    def __init__(self, connection_string: str) -> None:
        try:
            from azure.servicebus import ServiceBusClient  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("azure-servicebus is required for Service Bus provider") from exc

        self._client = ServiceBusClient.from_connection_string(connection_string)

    def create_topic(self, name: str) -> None:
        # Topic creation is typically handled via ARM/Bicep; log intent for now.
        logger.info("Ensure Service Bus topic exists", extra={"topic": name})

    def create_queue(self, name: str) -> None:
        logger.info("Ensure Service Bus queue exists", extra={"queue": name})

    def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        from azure.servicebus import ServiceBusMessage  # type: ignore

        with self._client:
            sender = self._client.get_topic_sender(topic_name=topic)
            with sender:
                sender.send_messages(ServiceBusMessage(json.dumps(payload)))

    def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        logger.warning("Service Bus subscription handling should be configured per-service.")


class AzureEventGridProvider(EventBusProvider):
    """Azure Event Grid provider implementation."""

    def __init__(self, endpoint: str, key: str) -> None:
        self._endpoint = endpoint
        self._key = key

    def create_topic(self, name: str) -> None:
        logger.info("Ensure Event Grid topic exists", extra={"topic": name})

    def create_queue(self, name: str) -> None:
        logger.info("Event Grid does not support queues", extra={"queue": name})

    def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        import httpx

        event = {
            "id": payload.get("id"),
            "eventType": payload.get("event_type"),
            "subject": payload.get("subject"),
            "eventTime": payload.get("time"),
            "data": payload.get("data"),
            "dataVersion": payload.get("version"),
        }
        headers = {"aeg-sas-key": self._key}
        url = f"{self._endpoint}/api/events"
        response = httpx.post(url, headers=headers, json=[event], timeout=10.0)
        response.raise_for_status()

    def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        logger.warning("Event Grid subscriptions are managed externally.")


class KafkaEventBusProvider(EventBusProvider):
    """Kafka provider implementation."""

    def __init__(self, bootstrap_servers: str) -> None:
        try:
            from kafka import KafkaProducer  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("kafka-python is required for Kafka provider") from exc

        self._bootstrap_servers = bootstrap_servers
        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        )

    def create_topic(self, name: str) -> None:
        logger.info("Ensure Kafka topic exists", extra={"topic": name})

    def create_queue(self, name: str) -> None:
        logger.info("Kafka does not support queues", extra={"queue": name})

    def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        self._producer.send(topic, payload)
        self._producer.flush()

    def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        try:
            from kafka import KafkaConsumer  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("kafka-python is required for Kafka provider") from exc

        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=self._bootstrap_servers,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        for message in consumer:
            handler(message.value)


class EventBusClient:
    """Unified client for publishing/subscribing to events."""

    def __init__(
        self,
        settings: Optional[EventBusSettings] = None,
        provider: Optional[EventBusProvider] = None,
        retry_policy: Optional[RetryPolicy] = None,
    ) -> None:
        self.settings = settings or EventBusSettings()
        self.retry_policy = retry_policy or RetryPolicy()
        self.provider = provider or self._build_provider()

    def _build_provider(self) -> EventBusProvider:
        match self.settings.provider:
            case "service_bus":
                if not self.settings.service_bus_connection_string:
                    raise ValueError("Service Bus connection string required")
                return AzureServiceBusProvider(self.settings.service_bus_connection_string)
            case "event_grid":
                if not self.settings.event_grid_endpoint or not self.settings.event_grid_key:
                    raise ValueError("Event Grid endpoint/key required")
                return AzureEventGridProvider(
                    self.settings.event_grid_endpoint,
                    self.settings.event_grid_key,
                )
            case "kafka":
                if not self.settings.kafka_bootstrap_servers:
                    raise ValueError("Kafka bootstrap servers required")
                return KafkaEventBusProvider(self.settings.kafka_bootstrap_servers)
            case _:
                return InMemoryEventBusProvider()

    def create_topic(self, name: Optional[str] = None) -> None:
        topic = name or self.settings.service_bus_topic
        self.provider.create_topic(topic)

    def create_queue(self, name: str) -> None:
        self.provider.create_queue(name)

    def publish_event(self, envelope: EventEnvelope) -> None:
        payload = envelope.to_payload()
        self._with_retry(lambda: self.provider.publish(self._topic_name(), payload))

    def subscribe(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        self.provider.subscribe(self._topic_name(), handler)

    def _topic_name(self) -> str:
        if self.settings.provider == "event_grid":
            return self.settings.event_grid_topic
        if self.settings.provider == "kafka":
            return self.settings.kafka_topic
        return self.settings.service_bus_topic

    def _with_retry(self, operation: Callable[[], None]) -> None:
        attempt = 0
        while True:
            try:
                operation()
                return
            except (ConnectionError, RuntimeError, TimeoutError, ValueError) as exc:
                attempt += 1
                if attempt >= self.retry_policy.max_attempts:
                    raise
                backoff = min(
                    self.retry_policy.backoff_seconds * (2 ** (attempt - 1)),
                    self.retry_policy.max_backoff_seconds,
                )
                logger.warning("Retrying event publish", extra={"error": str(exc)})
                time.sleep(backoff)


__all__ = [
    "EventEnvelope",
    "EventBusSettings",
    "EventBusClient",
    "RetryPolicy",
    "EventBusProvider",
    "InMemoryEventBusProvider",
    "KafkaEventBusProvider",
    "EventType",
    "ScheduleEventData",
    "RiskEventData",
    "ResourceEventData",
]
