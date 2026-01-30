from __future__ import annotations


class JSON:
    def __init__(self, *args, **kwargs) -> None:
        return None


class Column:
    def __init__(self, *args, **kwargs) -> None:
        return None


class DateTime:
    def __init__(self, *args, **kwargs) -> None:
        return None


class MetaData:
    def __init__(self, *args, **kwargs) -> None:
        return None


class String:
    def __init__(self, *args, **kwargs) -> None:
        return None


class Table:
    def __init__(self, *args, **kwargs) -> None:
        return None


class _Func:
    def __getattr__(self, name: str):
        return lambda *args, **kwargs: None


def select(*args, **kwargs):
    return None


func = _Func()
