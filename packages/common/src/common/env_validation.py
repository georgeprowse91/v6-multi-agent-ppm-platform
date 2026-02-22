from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

STRICT_ENVIRONMENTS = {"staging", "production"}
DEV_ENVIRONMENT_ALIASES = {"dev", "development", "local"}


@dataclass
class ValidationDiagnostics:
    missing: list[str]
    invalid_format: list[str]
    invalid_enum_or_range: list[str]

    @property
    def has_errors(self) -> bool:
        return bool(self.missing or self.invalid_format or self.invalid_enum_or_range)


def _normalize_location(error: Mapping[str, object]) -> str:
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


def normalize_environment(environment: str | None) -> str:
    if not environment:
        return "development"
    value = environment.strip().lower()
    if value == "prod":
        return "production"
    return value


def is_strict_environment(environment: str | None) -> bool:
    return normalize_environment(environment) in STRICT_ENVIRONMENTS


def classify_storage_backend(storage_value: str | Path) -> str:
    value = str(storage_value).strip().lower()
    if value.startswith(("postgresql://", "postgres://")):
        return "postgresql"
    if value.startswith(("mysql://", "mysql+pymysql://", "mariadb://")):
        return "mysql"
    if value.startswith(("redis://", "rediss://")):
        return "redis"
    if value.startswith(("sqlite://", "sqlite+aiosqlite://")):
        return "sqlite"
    return "file" if value.startswith("/") or value.endswith(".db") else "unknown"


def durability_mode_for_storage(storage_value: str | Path) -> str:
    backend = classify_storage_backend(storage_value)
    return "file-backed" if backend in {"sqlite", "file"} else "network-persistent"


def enforce_no_default_file_backed_storage(
    *,
    service_name: str,
    setting_names: tuple[str, ...],
    selected_value: str | Path,
    used_default: bool,
    environment: str | None,
    remediation_hint: str,
) -> None:
    if not used_default or not is_strict_environment(environment):
        return
    durability = durability_mode_for_storage(selected_value)
    if durability != "file-backed":
        return
    keys = " or ".join(setting_names)
    env_name = normalize_environment(environment)
    raise ValueError(
        f"[{service_name}] refusing fallback file-backed storage in {env_name}. "
        f"Set {keys}. {remediation_hint}"
    )


def environment_value(environ: Mapping[str, str] | None = None) -> str:
    env = environ or {}
    return normalize_environment(env.get("ENVIRONMENT"))
