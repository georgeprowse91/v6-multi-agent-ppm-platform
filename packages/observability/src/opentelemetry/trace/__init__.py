from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterator


class SpanKind(Enum):
    INTERNAL = 1
    SERVER = 2


class StatusCode(Enum):
    OK = 0
    ERROR = 1


@dataclass
class Status:
    status_code: StatusCode


class _SpanContext:
    trace_id: int = 0


class _Span:
    def __init__(self) -> None:
        self._context = _SpanContext()

    def get_span_context(self) -> _SpanContext:
        return self._context

    def set_attribute(self, key: str, value: Any) -> None:
        return None

    def set_status(self, status: Status) -> None:
        return None


class _Tracer:
    @contextmanager
    def start_as_current_span(
        self, name: str, context: Any | None = None, kind: SpanKind | None = None
    ) -> Iterator[_Span]:
        yield _Span()


_TRACER_PROVIDER: Any = None
_TRACER = _Tracer()


def set_tracer_provider(provider: Any) -> None:
    global _TRACER_PROVIDER
    _TRACER_PROVIDER = provider


def get_tracer(name: str) -> _Tracer:
    return _TRACER


def get_current_span() -> _Span:
    return _Span()


__all__ = ["SpanKind", "Status", "StatusCode", "get_tracer", "get_current_span", "set_tracer_provider"]
