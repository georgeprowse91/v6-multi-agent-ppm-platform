from pathlib import Path
from typing import Any, cast

import yaml
from jsonschema import Draft202012Validator, FormatChecker

PROMPT_DIR = Path(__file__).resolve().parent / "examples"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema" / "prompt.schema.json"


def list_prompts() -> list[Path]:
    return sorted(PROMPT_DIR.glob("*.prompt.yaml"))


def load_prompt(path: Path) -> dict[str, Any]:
    payload = cast(dict[str, Any], yaml.safe_load(path.read_text()))
    schema = cast(dict[str, Any], yaml.safe_load(SCHEMA_PATH.read_text()))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda err: err.path)
    if errors:
        formatted = "; ".join(error.message for error in errors)
        raise ValueError(f"Prompt validation failed: {formatted}")
    return payload
