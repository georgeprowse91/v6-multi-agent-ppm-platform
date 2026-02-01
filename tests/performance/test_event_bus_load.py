import pytest

from tests.helpers.service_bus import build_test_event_bus


@pytest.mark.asyncio
async def test_event_bus_handles_burst_load():
    event_bus = build_test_event_bus()
    received = 0

    def handler(payload: dict) -> None:
        nonlocal received
        received += 1

    event_bus.subscribe("load.test", handler)

    for idx in range(200):
        await event_bus.publish("load.test", {"index": idx})

    assert received == 200
    metrics = event_bus.get_metrics()
    assert metrics.get("load.test") == 200
