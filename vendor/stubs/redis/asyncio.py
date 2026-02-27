"""Stub redis.asyncio for tests without the real redis package."""
from __future__ import annotations


class Redis:
    """Stub async Redis client."""

    @classmethod
    def from_url(cls, url: str, **kwargs) -> "Redis":
        return cls()

    async def get(self, key: str):
        return None

    async def set(self, key: str, value, ex=None, **kwargs) -> bool:
        return True

    async def delete(self, key: str) -> int:
        return 0

    async def publish(self, channel: str, message: str) -> int:
        return 0

    async def aclose(self) -> None:
        pass

    async def close(self) -> None:
        pass

    def pubsub(self):
        return _PubSub()


def from_url(url: str, **kwargs) -> Redis:
    return Redis()


class _PubSub:
    async def subscribe(self, *channels) -> None:
        pass

    async def unsubscribe(self, *channels) -> None:
        pass

    async def get_message(self, **kwargs):
        return None

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration
