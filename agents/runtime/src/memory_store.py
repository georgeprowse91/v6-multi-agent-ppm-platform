from __future__ import annotations

import json
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any

import redis.asyncio as redis


class ConversationMemoryStore(ABC):
    """Abstract base class for conversation memory persistence."""

    @abstractmethod
    async def load(self, key: str) -> dict[str, Any]:
        """Load a stored context payload for a conversation key."""

    @abstractmethod
    async def save(self, key: str, payload: dict[str, Any]) -> None:
        """Persist a context payload for a conversation key."""

    async def close(self) -> None:
        """Close any underlying resources."""


class InMemoryConversationStore(ConversationMemoryStore):
    """In-memory conversation store for local development and tests."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    async def load(self, key: str) -> dict[str, Any]:
        return deepcopy(self._store.get(key, {}))

    async def save(self, key: str, payload: dict[str, Any]) -> None:
        self._store[key] = deepcopy(payload)


class RedisConversationStore(ConversationMemoryStore):
    """Redis-backed conversation store for durable orchestration context."""

    def __init__(
        self,
        client: redis.Redis,
        *,
        ttl_seconds: int | None = None,
        key_prefix: str = "conversation:",
    ) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds
        self._key_prefix = key_prefix

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        ttl_seconds: int | None = None,
        key_prefix: str = "conversation:",
        **kwargs: Any,
    ) -> "RedisConversationStore":
        client = redis.from_url(url, **kwargs)
        return cls(client, ttl_seconds=ttl_seconds, key_prefix=key_prefix)

    async def load(self, key: str) -> dict[str, Any]:
        payload = await self._client.get(self._key_prefix + key)
        if payload is None:
            return {}
        return json.loads(payload)

    async def save(self, key: str, payload: dict[str, Any]) -> None:
        data = json.dumps(payload)
        namespaced_key = self._key_prefix + key
        if self._ttl_seconds is not None:
            await self._client.setex(namespaced_key, self._ttl_seconds, data)
        else:
            await self._client.set(namespaced_key, data)

    async def close(self) -> None:
        await self._client.close()
