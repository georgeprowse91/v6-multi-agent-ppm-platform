from __future__ import annotations

from typing import Any


class TracerProvider:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._processors: list[Any] = []

    def add_span_processor(self, processor: Any) -> None:
        self._processors.append(processor)
