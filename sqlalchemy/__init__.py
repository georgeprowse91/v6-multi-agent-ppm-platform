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


class Float:
    def __init__(self, *args, **kwargs) -> None:
        return None


class Integer:
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


class _Engine:
    def begin(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def execute(self, *args, **kwargs):
        return None


def create_engine(*args, **kwargs):
    return _Engine()
