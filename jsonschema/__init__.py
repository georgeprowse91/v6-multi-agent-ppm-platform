from __future__ import annotations

from collections.abc import Iterable


class FormatChecker:
    def __init__(self, *args, **kwargs) -> None:
        return None


class Draft202012Validator:
    def __init__(self, schema, format_checker: FormatChecker | None = None) -> None:
        self.schema = schema
        self.format_checker = format_checker

    def iter_errors(self, instance) -> Iterable[Exception]:
        return []


class ValidationError(Exception):
    pass


def validate(instance, schema) -> None:
    return None
