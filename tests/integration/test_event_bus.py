from integrations.services.integration.event_bus import (
    EventBusClient,
    EventBusSettings,
    EventEnvelope,
    InMemoryEventBusProvider,
    RetryPolicy,
)


def test_publish_and_subscribe_in_memory_event_bus():
    provider = InMemoryEventBusProvider()
    settings = EventBusSettings(provider="in_memory")
    client = EventBusClient(settings=settings, provider=provider)

    received = []

    def handler(payload):
        received.append(payload)

    client.subscribe(handler)

    event = EventEnvelope(event_type="schedule.created", subject="schedule/1", data={"id": 1})
    client.publish_event(event)

    assert received
    assert received[0]["event_type"] == "schedule.created"


def test_retry_policy_retries_transient_errors():
    calls = {"count": 0}

    class FailingProvider(InMemoryEventBusProvider):
        def publish(self, topic, payload):
            calls["count"] += 1
            if calls["count"] < 2:
                raise RuntimeError("Transient")
            super().publish(topic, payload)

    provider = FailingProvider()
    settings = EventBusSettings(provider="in_memory")
    client = EventBusClient(
        settings=settings,
        provider=provider,
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0.0),
    )

    event = EventEnvelope(event_type="schedule.created", subject="schedule/2")
    client.publish_event(event)

    assert calls["count"] == 2
