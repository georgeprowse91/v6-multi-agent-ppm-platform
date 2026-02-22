"""Minimal SQLAlchemy asyncio extension stub for offline environments."""

from __future__ import annotations


class _AsyncResult:
    """Async-compatible result stub."""

    def scalar_one_or_none(self):
        return None

    def scalar(self):
        return None

    def scalars(self):
        return self

    def all(self):
        return []

    def first(self):
        return None

    def fetchall(self):
        return []

    def fetchone(self):
        return None

    def __iter__(self):
        return iter([])


class _AsyncConnection:
    """Async connection stub."""

    async def execute(self, *args, **kwargs):
        return _AsyncResult()

    async def run_sync(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def close(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class AsyncSession:
    """Async session stub."""

    def __init__(self, *args, **kwargs):
        self._items: list = []

    async def execute(self, *args, **kwargs):
        return _AsyncResult()

    async def scalar(self, *args, **kwargs):
        return None

    async def get(self, model, pk, *args, **kwargs):
        return None

    def add(self, obj):
        self._items.append(obj)

    async def merge(self, obj):
        return obj

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def close(self):
        pass

    async def flush(self):
        pass

    async def refresh(self, obj):
        pass

    async def delete(self, obj):
        pass

    def begin(self):
        """Return a transaction context manager (used as async with session.begin():)."""
        return _AsyncConnection()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _AsyncEngine:
    """Async engine stub."""

    def begin(self):
        return _AsyncConnection()

    def connect(self):
        return _AsyncConnection()

    async def dispose(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def create_async_engine(*args, **kwargs):
    return _AsyncEngine()


def async_sessionmaker(*args, **kwargs):
    class _AsyncSessionFactory:
        def __init__(self, *a, **kw):
            pass

        def __call__(self, *a, **kw):
            return AsyncSession()

        async def __aenter__(self):
            return AsyncSession()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    return _AsyncSessionFactory
