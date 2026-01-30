from __future__ import annotations

from typing import Any


class _NoopPropagator:
    def inject(self, carrier: dict[str, str]) -> None:
        return None

    def extract(self, carrier: dict[str, str]) -> dict[str, str]:
        return carrier


_GLOBAL_PROPAGATOR: _NoopPropagator = _NoopPropagator()


def set_global_textmap(propagator: Any) -> None:
    global _GLOBAL_PROPAGATOR
    _GLOBAL_PROPAGATOR = propagator


def inject(carrier: dict[str, str]) -> None:
    _GLOBAL_PROPAGATOR.inject(carrier)


def extract(carrier: dict[str, str]) -> dict[str, str]:
    return _GLOBAL_PROPAGATOR.extract(carrier)
