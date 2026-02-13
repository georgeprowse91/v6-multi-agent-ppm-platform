from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from pydantic import ValidationError


@dataclass
class ValidationDiagnostics:
    missing: list[str]
    invalid_format: list[str]
    invalid_enum_or_range: list[str]

    @property
    def has_errors(self) -> bool:
        return bool(self.missing or self.invalid_format or self.invalid_enum_or_range)


def _normalize_location(error: dict[str, object]) -> str:
    loc = error.get("loc", ())
    if not isinstance(loc, (tuple, list)):
        return str(loc)
    return ".".join(str(item) for item in loc)


def build_validation_diagnostics(exc: ValidationError) -> ValidationDiagnostics:
    grouped: dict[str, list[str]] = defaultdict(list)
    for error in exc.errors(include_url=False):
        error_type = str(error.get("type", ""))
        field_name = _normalize_location(error)
        message = str(error.get("msg", "Invalid value"))
        diagnostic = f"{field_name}: {message}"
        if error_type == "missing":
            grouped["missing"].append(diagnostic)
        elif any(
            token in error_type
            for token in (
                "enum",
                "literal",
                "greater_than",
                "less_than",
                "too_short",
                "too_long",
            )
        ):
            grouped["invalid_enum_or_range"].append(diagnostic)
        else:
            grouped["invalid_format"].append(diagnostic)

    return ValidationDiagnostics(
        missing=sorted(grouped["missing"]),
        invalid_format=sorted(grouped["invalid_format"]),
        invalid_enum_or_range=sorted(grouped["invalid_enum_or_range"]),
    )


def format_validation_report(service_name: str, diagnostics: ValidationDiagnostics) -> str:
    lines = [f"[{service_name}] configuration validation failed"]

    def _emit(title: str, entries: list[str]) -> None:
        if not entries:
            return
        lines.append(f"- {title}:")
        lines.extend(f"  • {entry}" for entry in entries)

    _emit("Missing required values", diagnostics.missing)
    _emit("Invalid format", diagnostics.invalid_format)
    _emit("Invalid enum/range", diagnostics.invalid_enum_or_range)

    return "\n".join(lines)
