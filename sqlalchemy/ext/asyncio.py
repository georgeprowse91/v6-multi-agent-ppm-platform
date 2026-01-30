from __future__ import annotations


class AsyncSession:
    def __init__(self, *args, **kwargs) -> None:
        return None


def async_sessionmaker(*args, **kwargs):
    def _factory(*args, **kwargs):  # noqa: ANN001, ANN002
        return AsyncSession()

    return _factory


def create_async_engine(*args, **kwargs):
    return None
