"""Real-time execution event infrastructure for copilot streaming."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger("agents.runtime.execution_events")


class ExecutionEventType(StrEnum):
    orchestration_started = "orchestration_started"
    orchestration_completed = "orchestration_completed"
    agent_started = "agent_started"
    agent_thinking = "agent_thinking"
    agent_intermediate = "agent_intermediate"
    agent_completed = "agent_completed"
    agent_error = "agent_error"


_AGENT_EVENT_TYPES = {
    ExecutionEventType.agent_started,
    ExecutionEventType.agent_thinking,
    ExecutionEventType.agent_intermediate,
    ExecutionEventType.agent_completed,
    ExecutionEventType.agent_error,
}


class ExecutionEvent(BaseModel):
    """A single execution event emitted during orchestration."""

    event_type: ExecutionEventType
    task_id: str = ""
    agent_id: str = ""
    catalog_id: str = ""
    correlation_id: str = ""
    timestamp: float = Field(default_factory=time.time)
    data: dict[str, Any] = Field(default_factory=dict)
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate_agent_fields(self) -> ExecutionEvent:
        if self.event_type in _AGENT_EVENT_TYPES:
            if not self.task_id:
                raise ValueError(
                    "task_id must be non-empty for %s events" % self.event_type
                )
            if not self.agent_id:
                raise ValueError(
                    "agent_id must be non-empty for %s events" % self.event_type
                )
        return self


_DEFAULT_MAX_QUEUE_SIZE = 1000


class ExecutionEventEmitter:
    """Queue-based emitter for a single orchestration correlation."""

    def __init__(self, correlation_id: str, max_queue_size: int = _DEFAULT_MAX_QUEUE_SIZE) -> None:
        self.correlation_id = correlation_id
        self._queue: asyncio.Queue[ExecutionEvent | None] = asyncio.Queue(
            maxsize=max_queue_size,
        )
        logger.info("Created emitter for correlation %s (max_queue_size=%d)", correlation_id, max_queue_size)

    async def emit(self, event: ExecutionEvent) -> None:
        event.correlation_id = self.correlation_id
        await self._queue.put(event)

    async def complete(self) -> None:
        logger.info("Completing emitter for correlation %s", self.correlation_id)
        await self._queue.put(None)

    async def __aiter__(self):
        return self

    async def __anext__(self) -> ExecutionEvent:
        item = await self._queue.get()
        if item is None:
            raise StopAsyncIteration
        return item

    async def get(self, timeout: float | None = None) -> ExecutionEvent | None:
        try:
            if timeout is not None:
                return await asyncio.wait_for(self._queue.get(), timeout=timeout)
            return await self._queue.get()
        except asyncio.TimeoutError:
            return None


class ExecutionEventRegistry:
    """Singleton registry of active event emitters keyed by correlation_id."""

    _instance: ExecutionEventRegistry | None = None

    def __init__(self) -> None:
        self._emitters: dict[str, ExecutionEventEmitter] = {}

    @classmethod
    def get_instance(cls) -> ExecutionEventRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_emitter(self, correlation_id: str | None = None) -> ExecutionEventEmitter:
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        emitter = ExecutionEventEmitter(correlation_id)
        self._emitters[correlation_id] = emitter
        return emitter

    def get_emitter(self, correlation_id: str) -> ExecutionEventEmitter | None:
        return self._emitters.get(correlation_id)

    def remove_emitter(self, correlation_id: str) -> None:
        removed = self._emitters.pop(correlation_id, None)
        if removed is not None:
            logger.info("Removed emitter for correlation %s", correlation_id)

    def list_active(self) -> list[str]:
        """Return list of active correlation_ids."""
        return list(self._emitters.keys())
