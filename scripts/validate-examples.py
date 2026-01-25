#!/usr/bin/env python3
"""Validate example JSON payloads used in docs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from jsonschema import Draft202012Validator

DEFAULT_EXAMPLES = [
    Path("examples/portfolio-intake-request.json"),
]

SCHEMA_PATH = Path("examples/schema/portfolio-intake.schema.json")


class ExampleValidationError(Exception):
    pass


def _load_json(path: Path) -> dict:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ExampleValidationError(f"Example {path} must be a JSON object")
    return data


def validate_example(path: Path) -> None:
    if not SCHEMA_PATH.exists():
        raise ExampleValidationError(f"Missing schema: {SCHEMA_PATH}")
    schema = json.loads(SCHEMA_PATH.read_text())
    example = _load_json(path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(example), key=lambda e: e.path)
    if errors:
        formatted = "\n".join(f"- {error.message}" for error in errors)
        raise ExampleValidationError(f"Schema validation failed for {path}:\n{formatted}")


def validate_examples(paths: Iterable[Path]) -> None:
    for path in paths:
        if not path.exists():
            raise ExampleValidationError(f"Missing example file: {path}")
        validate_example(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate JSON examples.")
    parser.add_argument("paths", nargs="*", type=Path, help="Optional example paths")
    args = parser.parse_args()
    examples = list(args.paths or DEFAULT_EXAMPLES)
    validate_examples(examples)
    print(f"Validated {len(examples)} example file(s) successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
