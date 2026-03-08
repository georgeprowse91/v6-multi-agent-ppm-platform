"""Tests for the execution events infrastructure (Enhancement 1)."""

from __future__ import annotations

import asyncio

import pytest

from agents.runtime.src.execution_events import (
    ExecutionEvent,
    ExecutionEventEmitter,
    ExecutionEventRegistry,
    ExecutionEventType,
)


@pytest.mark.asyncio
async def test_emitter_emit_and_get():
    emitter = ExecutionEventEmitter("corr-1")
    event = ExecutionEvent(
        event_type=ExecutionEventType.agent_started,
        task_id="t1",
        agent_id="a1",
    )
    await emitter.emit(event)
    received = await emitter.get(timeout=1.0)
    assert received is not None
    assert received.event_type == ExecutionEventType.agent_started
    assert received.task_id == "t1"
    assert received.correlation_id == "corr-1"


@pytest.mark.asyncio
async def test_emitter_complete_stops_iteration():
    emitter = ExecutionEventEmitter("corr-2")
    await emitter.emit(ExecutionEvent(event_type=ExecutionEventType.orchestration_started))
    await emitter.complete()
    event = await emitter.get(timeout=1.0)
    assert event is not None
    assert event.event_type == ExecutionEventType.orchestration_started
    # Next get should return None (sentinel)
    sentinel = await emitter.get(timeout=1.0)
    assert sentinel is None


@pytest.mark.asyncio
async def test_emitter_get_timeout():
    emitter = ExecutionEventEmitter("corr-3")
    result = await emitter.get(timeout=0.05)
    assert result is None


def test_registry_create_and_get():
    registry = ExecutionEventRegistry()
    emitter = registry.create_emitter("test-corr")
    assert registry.get_emitter("test-corr") is emitter


def test_registry_remove():
    registry = ExecutionEventRegistry()
    registry.create_emitter("to-remove")
    registry.remove_emitter("to-remove")
    assert registry.get_emitter("to-remove") is None


def test_registry_get_nonexistent():
    registry = ExecutionEventRegistry()
    assert registry.get_emitter("nope") is None


def test_execution_event_model():
    event = ExecutionEvent(
        event_type=ExecutionEventType.agent_completed,
        task_id="t1",
        agent_id="agent-x",
        confidence_score=0.85,
        data={"success": True},
    )
    assert event.event_type == ExecutionEventType.agent_completed
    assert event.confidence_score == 0.85
    dumped = event.model_dump()
    assert dumped["agent_id"] == "agent-x"


# --- Error path and edge case tests ---


@pytest.mark.asyncio
async def test_emitter_multiple_events_ordered():
    """Events should be received in the order they were emitted."""
    emitter = ExecutionEventEmitter("corr-order")
    for i in range(5):
        await emitter.emit(
            ExecutionEvent(
                event_type=ExecutionEventType.agent_intermediate,
                task_id=f"t{i}",
                agent_id="a1",
                data={"index": i},
            )
        )
    for i in range(5):
        event = await emitter.get(timeout=1.0)
        assert event is not None
        assert event.data["index"] == i


@pytest.mark.asyncio
async def test_emitter_concurrent_emit_and_consume():
    """Emit and consume concurrently without deadlock."""
    emitter = ExecutionEventEmitter("corr-concurrent")
    received = []

    async def producer():
        for i in range(20):
            await emitter.emit(
                ExecutionEvent(
                    event_type=ExecutionEventType.agent_thinking,
                    task_id=f"t{i}",
                    agent_id="a1",
                    data={"i": i},
                )
            )
        await emitter.complete()

    async def consumer():
        while True:
            item = await emitter.get(timeout=2.0)
            if item is None:
                break
            received.append(item)

    await asyncio.gather(producer(), consumer())
    assert len(received) == 20


@pytest.mark.asyncio
async def test_emitter_get_no_timeout_blocks():
    """get() without timeout should block until an event arrives."""
    emitter = ExecutionEventEmitter("corr-block")

    async def delayed_emit():
        await asyncio.sleep(0.05)
        await emitter.emit(
            ExecutionEvent(
                event_type=ExecutionEventType.agent_started, task_id="delayed", agent_id="a1"
            )
        )

    asyncio.create_task(delayed_emit())
    event = await asyncio.wait_for(emitter.get(), timeout=2.0)
    assert event is not None
    assert event.task_id == "delayed"


def test_registry_create_auto_id():
    """create_emitter without correlation_id should generate one."""
    registry = ExecutionEventRegistry()
    emitter = registry.create_emitter()
    assert emitter.correlation_id
    assert registry.get_emitter(emitter.correlation_id) is emitter


def test_registry_remove_nonexistent_is_noop():
    """Removing a non-existent emitter should not raise."""
    registry = ExecutionEventRegistry()
    registry.remove_emitter("does-not-exist")  # Should not raise


def test_registry_overwrite_existing():
    """Creating an emitter with an existing correlation_id should replace."""
    registry = ExecutionEventRegistry()
    emitter1 = registry.create_emitter("dup-id")
    emitter2 = registry.create_emitter("dup-id")
    assert registry.get_emitter("dup-id") is emitter2
    assert emitter1 is not emitter2


def test_event_all_types():
    """Every ExecutionEventType value should be constructable."""
    for event_type in ExecutionEventType:
        kwargs = {"event_type": event_type}
        if event_type.startswith("agent_"):
            kwargs["task_id"] = "t1"
            kwargs["agent_id"] = "a1"
        event = ExecutionEvent(**kwargs)
        assert event.event_type == event_type


def test_event_default_timestamp():
    """Event should have a non-zero timestamp by default."""
    event = ExecutionEvent(event_type=ExecutionEventType.orchestration_started)
    assert event.timestamp > 0


def test_event_data_isolation():
    """Data dicts should not be shared between event instances."""
    e1 = ExecutionEvent(event_type=ExecutionEventType.orchestration_started)
    e2 = ExecutionEvent(event_type=ExecutionEventType.orchestration_started)
    e1.data["key"] = "value"
    assert "key" not in e2.data
