from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


@dataclass(frozen=True)
class SchemaValidationError:
    message: str
    path: str


def _load_schema(schema_path: Path) -> dict[str, Any]:
    return json.loads(schema_path.read_text())


def validate_instance(instance: Any, schema_path: Path) -> list[SchemaValidationError]:
    schema = _load_schema(schema_path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda err: err.path)
    return [
        SchemaValidationError(
            message=error.message,
            path="/" + "/".join(str(part) for part in error.path),
        )
        for error in errors
    ]
