"""Reusable mock objects for PPM platform tests.

These classes mirror the mocks already defined in ``tests/conftest.py``
but are importable as standalone objects for use in any test module.
"""

from __future__ import annotations

from typing import Any


class MockAzureOpenAI:
    """Lightweight stand-in for the Azure OpenAI client.

    Records every call for later inspection.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []

    def chat_completions(self, prompt: str) -> dict[str, Any]:
        """Simulate a chat completion request."""
        self.calls.append(prompt)
        return {
            "id": "mock-response",
            "choices": [{"message": {"content": "ok"}}],
        }


class MockDatabase:
    """In-memory mock for a database connection.

    Stores every executed query for assertion in tests.
    """

    def __init__(self) -> None:
        self.queries: list[dict[str, Any]] = []

    def execute(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Record and return an empty result set."""
        self.queries.append({"query": query, "params": params or {}})
        return []


class MockRedis:
    """In-memory mock for a Redis connection."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        """Get a value by key."""
        return self.store.get(key)

    def set(self, key: str, value: str) -> bool:
        """Set a value by key."""
        self.store[key] = value
        return True

    def delete(self, key: str) -> bool:
        """Delete a key."""
        return self.store.pop(key, None) is not None

    def exists(self, key: str) -> bool:
        """Check if a key exists."""
        return key in self.store


class MockEventBus:
    """In-memory mock for the platform event bus.

    Collects published events for assertion.
    """

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Record a published event."""
        self.events.append({"topic": topic, "payload": payload})

    def get_events(self, topic: str | None = None) -> list[dict[str, Any]]:
        """Return recorded events, optionally filtered by topic."""
        if topic is None:
            return list(self.events)
        return [e for e in self.events if e["topic"] == topic]


class MockStateStore:
    """In-memory mock for agent state persistence."""

    def __init__(self) -> None:
        self._state: dict[str, Any] = {}

    async def get(self, key: str) -> Any:
        """Retrieve state by key."""
        return self._state.get(key)

    async def set(self, key: str, value: Any) -> None:
        """Persist state by key."""
        self._state[key] = value

    async def delete(self, key: str) -> None:
        """Remove state by key."""
        self._state.pop(key, None)
