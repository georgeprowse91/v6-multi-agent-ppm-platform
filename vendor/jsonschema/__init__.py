from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Sequence


class FormatChecker:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        return None


class Draft202012Validator:
    def __init__(self, schema: dict[str, Any], format_checker: FormatChecker | None = None) -> None:
        self.schema = schema
        self.format_checker = format_checker

    def iter_errors(self, instance: dict[str, Any]) -> Iterable[ValidationError]:
        return []


class ValidationError(Exception):
    def __init__(self, message: str, path: Sequence[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.path = list(path or [])


def validate(instance: dict[str, Any], schema: dict[str, Any]) -> None:
    return None
