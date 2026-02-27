"""Minimal redis stub for tests that don't have the redis package installed."""
from __future__ import annotations


class Redis:
    """Stub synchronous Redis client."""

    @classmethod
    def from_url(cls, url: str, **kwargs) -> "Redis":
        return cls()

    def get(self, key: str):
        return None

    def set(self, key: str, value, ex=None, nx=False, **kwargs) -> bool:
        return True

    def rpush(self, key: str, *values) -> int:
        return len(values)

    def lrange(self, key: str, start: int, end: int) -> list:
        return []

    def delete(self, key: str) -> int:
        return 0

    def close(self) -> None:
        pass
