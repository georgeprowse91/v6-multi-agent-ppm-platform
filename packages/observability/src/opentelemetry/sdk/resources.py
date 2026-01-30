from __future__ import annotations


class Resource:
    def __init__(self, attributes: dict[str, str] | None = None) -> None:
        self.attributes = attributes or {}

    @classmethod
    def create(cls, attributes: dict[str, str]) -> "Resource":
        return cls(attributes=attributes)
