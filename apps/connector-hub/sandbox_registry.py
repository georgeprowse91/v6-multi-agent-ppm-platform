from pathlib import Path
from typing import Any, cast

import yaml
from jsonschema import Draft202012Validator, FormatChecker

SANDBOX_CONFIG_DIR = Path(__file__).resolve().parent / "sandbox" / "examples"
SCHEMA_PATH = Path(__file__).resolve().parent / "sandbox" / "schema" / "sandbox-connector.schema.json"


def list_sandbox_configs() -> list[Path]:
    return sorted(SANDBOX_CONFIG_DIR.glob("*.yaml"))


def load_sandbox_config(path: Path) -> dict[str, Any]:
    payload = cast(dict[str, Any], yaml.safe_load(path.read_text()))
    schema = cast(dict[str, Any], yaml.safe_load(SCHEMA_PATH.read_text()))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda err: err.path)
    if errors:
        formatted = "; ".join(error.message for error in errors)
        raise ValueError(f"Sandbox config validation failed: {formatted}")
    return payload
