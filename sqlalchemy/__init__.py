"""Minimal SQLAlchemy shim for tests."""

from __future__ import annotations

from dataclasses import dataclass


class _Type:
    def __init__(self, *args, **kwargs):
        pass


DateTime = Float = Integer = String = JSON = Text = Date = Numeric = _Type


class Column:
    def __init__(self, *args, primary_key: bool = False, nullable: bool = True, default=None, **kwargs):
        self.args = args
        self.primary_key = primary_key
        self.nullable = nullable
        self.default = default


class MetaData:
    pass


class Table:
    def __init__(self, *args, **kwargs):
        self.args = args


class _Func:
    @staticmethod
    def now():
        return "now"


func = _Func()


def create_engine(*args, **kwargs):
    return object()


def ForeignKey(*args, **kwargs):
    return ("ForeignKey", args, kwargs)


def select(*args, **kwargs):
    return ("select", args)


def text(value: str):
    return value


def engine_from_config(*args, **kwargs):
    return object()


class pool:
    class NullPool:
        pass
