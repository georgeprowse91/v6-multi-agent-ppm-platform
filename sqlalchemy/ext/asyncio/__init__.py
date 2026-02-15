from __future__ import annotations


class AsyncSession:
    pass


def async_sessionmaker(*args, **kwargs):
    class _Factory:
        def __call__(self, *a, **k):
            return AsyncSession()

    return _Factory()


def create_async_engine(*args, **kwargs):
    return object()
