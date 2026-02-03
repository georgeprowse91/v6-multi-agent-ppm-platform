from __future__ import annotations

from typing import Any, Callable


class JSON:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        return None


class Column:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        return None


class DateTime:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        return None


class MetaData:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        return None


class String:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        return None


class Float:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        return None


class Integer:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        return None


class _ColumnCollection:
    def __getattr__(self, name: str) -> Column:
        return Column(name)


class _Statement:
    def where(self, *args: Any, **kwargs: Any) -> _Statement:
        return self

    def values(self, *args: Any, **kwargs: Any) -> _Statement:
        return self


class Table:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.c = _ColumnCollection()

    def insert(self) -> _Statement:
        return _Statement()

    def update(self) -> _Statement:
        return _Statement()


class _Func:
    def __getattr__(self, name: str) -> Callable[..., Any]:
        return lambda *args, **kwargs: None


def select(*args: Any, **kwargs: Any) -> _Statement:
    return _Statement()


func = _Func()


class _Engine:
    def begin(self) -> _Engine:
        return self

    def __enter__(self) -> _Engine:
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def execute(self, *args: Any, **kwargs: Any) -> None:
        return None


def create_engine(*args: Any, **kwargs: Any) -> _Engine:
    return _Engine()
