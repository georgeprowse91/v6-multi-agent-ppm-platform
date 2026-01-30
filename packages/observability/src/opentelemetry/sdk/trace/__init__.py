from __future__ import annotations


class TracerProvider:
    def __init__(self, *args, **kwargs) -> None:
        self._processors = []

    def add_span_processor(self, processor) -> None:
        self._processors.append(processor)
