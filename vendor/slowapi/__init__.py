"""Minimal slowapi stub with functional in-memory rate limiting."""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import Request, Response


def get_remote_address(request: Request) -> str:
    return request.client.host if request.client else "127.0.0.1"


def _parse_limit(limit_string: str) -> tuple[int, int]:
    """Parse '100/minute' → (100, 60 seconds)."""
    parts = limit_string.split("/")
    count = int(parts[0].strip())
    period = parts[1].strip().lower() if len(parts) > 1 else "minute"
    seconds = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}.get(period, 60)
    return count, seconds


class _RateLimitBucket:
    """Sliding-window in-memory rate-limit bucket."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._counts: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.window_seconds
        with self._lock:
            self._counts[key] = [t for t in self._counts[key] if t > window_start]
            if len(self._counts[key]) >= self.limit:
                return False
            self._counts[key].append(now)
            return True


class Limiter:
    def __init__(self, key_func=None, default_limits=None, **kwargs):
        self._key_func = key_func or get_remote_address
        self._default_limits = default_limits or []
        self._default_buckets: list[_RateLimitBucket] = []
        for limit_str in self._default_limits:
            count, seconds = _parse_limit(limit_str)
            self._default_buckets.append(_RateLimitBucket(count, seconds))

    def limit(self, limit_string: str):
        """Per-route rate-limit decorator (no-op; default limits apply via middleware)."""
        def decorator(func):
            return func
        return decorator

    def exempt(self, func):
        """Mark a route as exempt from default rate limits."""
        func._rate_limit_exempt = True
        return func

    def is_rate_limited(self, key: str) -> bool:
        for bucket in self._default_buckets:
            if not bucket.is_allowed(key):
                return True
        return False


async def _rate_limit_exceeded_handler(request: Request, exc: Exception) -> Response:
    return Response("Rate limit exceeded", status_code=429)
