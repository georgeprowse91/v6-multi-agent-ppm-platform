#!/usr/bin/env python3
"""Validate agent prompt definitions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import yaml
from jsonschema import Draft202012Validator

DEFAULT_PROMPTS = [
    Path("agents/runtime/prompts/examples/intent-router.prompt.yaml"),
]

SCHEMA_PATH = Path("agents/runtime/prompts/schema/prompt.schema.json")


class PromptValidationError(Exception):
    pass


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise PromptValidationError(f"Prompt {path} must be a YAML mapping")
    return data


def validate_prompt(path: Path) -> None:
    if not SCHEMA_PATH.exists():
        raise PromptValidationError(f"Missing schema: {SCHEMA_PATH}")
    schema = json.loads(SCHEMA_PATH.read_text())
    prompt = _load_yaml(path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(prompt), key=lambda e: e.path)
    if errors:
        formatted = "\n".join(f"- {error.message}" for error in errors)
        raise PromptValidationError(f"Schema validation failed for {path}:\n{formatted}")


def validate_prompts(paths: Iterable[Path]) -> None:
    for path in paths:
        if not path.exists():
            raise PromptValidationError(f"Missing prompt definition: {path}")
        validate_prompt(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate prompt definitions.")
    parser.add_argument("paths", nargs="*", type=Path, help="Optional prompt paths")
    args = parser.parse_args()
    prompts = list(args.paths or DEFAULT_PROMPTS)
    validate_prompts(prompts)
    print(f"Validated {len(prompts)} prompt definition(s) successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
