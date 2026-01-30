from __future__ import annotations

from typing import Any


class _DummyMetric:
    def add(self, value: float, attributes: dict[str, Any] | None = None) -> None:
        return None

    def record(self, value: float, attributes: dict[str, Any] | None = None) -> None:
        return None


class _DummyMeter:
    def create_counter(self, *args: Any, **kwargs: Any) -> _DummyMetric:
        return _DummyMetric()

    def create_histogram(self, *args: Any, **kwargs: Any) -> _DummyMetric:
        return _DummyMetric()


_METER_PROVIDER: Any = None
_METER = _DummyMeter()


def set_meter_provider(provider: Any) -> None:
    global _METER_PROVIDER
    _METER_PROVIDER = provider


def get_meter(name: str) -> _DummyMeter:
    return _METER
