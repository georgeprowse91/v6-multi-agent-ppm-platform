from __future__ import annotations


class TraceContextTextMapPropagator:
    def inject(self, carrier: dict[str, str]) -> None:
        return None

    def extract(self, carrier: dict[str, str]) -> dict[str, str]:
        return carrier
