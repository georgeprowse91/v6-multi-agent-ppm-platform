from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

import yaml

from jsonschema import Draft202012Validator, FormatChecker

PROMPT_DIR = Path(__file__).resolve().parent / "examples"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema" / "prompt.schema.json"
REDACTION_KEYS = {"password", "secret", "token", "api_key", "ssn"}


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


def load_prompt_by_agent(agent: str, purpose: str) -> dict[str, Any]:
    for path in list_prompts():
        prompt = load_prompt(path)
        metadata = prompt.get("metadata", {})
        if metadata.get("agent") == agent and metadata.get("purpose") == purpose:
            return prompt
    raise ValueError(f"No prompt found for agent={agent} purpose={purpose}")


def _redact_value(value: Any, strategy: str) -> Any:
    if strategy == "drop":
        return None
    return "[REDACTED]"


def _apply_redaction(
    payload: dict[str, Any],
    fields: Iterable[str],
    strategy: str,
) -> dict[str, Any]:
    def match_key(mapping: dict[str, Any], part: str) -> str | None:
        if part in mapping:
            return part
        lowered = part.lower()
        if lowered in REDACTION_KEYS:
            for key in mapping:
                if key.lower() == lowered:
                    return key
        return None

    def apply_path(target: Any, parts: list[str]) -> None:
        if not parts:
            return
        if isinstance(target, list):
            for item in target:
                apply_path(item, parts)
            return
        if not isinstance(target, dict):
            return
        key = match_key(target, parts[0])
        if key is None:
            return
        if len(parts) == 1:
            target[key] = _redact_value(target[key], strategy)
            return
        apply_path(target[key], parts[1:])

    redacted = dict(payload)
    for field in fields:
        apply_path(redacted, field.split("."))
    return redacted


def enforce_redaction(prompt: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    redaction_cfg = prompt.get("prompt", {}).get("redaction")
    if not redaction_cfg:
        return payload
    strategy = redaction_cfg.get("strategy", "mask")
    fields = set(redaction_cfg.get("fields", []))
    if redaction_cfg.get("pii"):
        fields.update({"user.email", "user.phone", "user.ssn"})
    if redaction_cfg.get("secrets"):
        fields.update({f"secrets.{key}" for key in REDACTION_KEYS})
    return _apply_redaction(payload, fields, strategy)
