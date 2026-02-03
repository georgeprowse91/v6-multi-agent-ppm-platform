from __future__ import annotations

from typing import Any, Generic, TypeVar, cast

_TAsyncSession = TypeVar("_TAsyncSession", bound="AsyncSession")


class AsyncSession:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        return None

    async def __aenter__(self) -> AsyncSession:
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def execute(self, *args: Any, **kwargs: Any) -> _Result:
        return _Result()

    def begin(self) -> _AsyncSessionTransaction:
        return _AsyncSessionTransaction()


class _AsyncSessionTransaction:
    async def __aenter__(self) -> _AsyncSessionTransaction:
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None


class _Result:
    rowcount: int = 0

    def fetchall(self) -> list[Any]:
        return []


class async_sessionmaker(Generic[_TAsyncSession]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        return None

    def __call__(self) -> _TAsyncSession:
        return cast(_TAsyncSession, AsyncSession())


def create_async_engine(*args: Any, **kwargs: Any) -> Any:
    return None
