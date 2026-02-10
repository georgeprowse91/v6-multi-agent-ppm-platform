"""Validate ops/config YAML/JSON files against JSON Schemas in ops/schemas."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

DEFAULT_CONFIG_DIR = REPO_ROOT / "ops" / "config"
DEFAULT_SCHEMA_DIR = REPO_ROOT / "ops" / "schemas"


@dataclass(frozen=True)
class ValidationIssue:
    config_path: Path
    message: str
    line: int


@dataclass(frozen=True)
class SchemaIssue:
    path: tuple[Any, ...]
    message: str


def _schema_name_for(config_path: Path) -> str:
    return f"{config_path.stem}.schema.json"


def _iter_config_files(config_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in config_dir.rglob("*")
        if path.is_file() and path.suffix in {".yaml", ".yml", ".json"} and not path.name.endswith(".schema.json")
    )


def _key_from_node(node: ScalarNode) -> Any:
    if node.tag.endswith(":int"):
        return int(node.value)
    if node.tag.endswith(":float"):
        return float(node.value)
    if node.tag.endswith(":bool"):
        return node.value.lower() == "true"
    if node.tag.endswith(":null"):
        return None
    return node.value


def _build_line_map(node: Node | None, path: tuple[Any, ...] = ()) -> dict[tuple[Any, ...], int]:
    if node is None:
        return {}

    line_map: dict[tuple[Any, ...], int] = {path: node.start_mark.line + 1}

    if isinstance(node, MappingNode):
        for key_node, value_node in node.value:
            if not isinstance(key_node, ScalarNode):
                continue
            key = _key_from_node(key_node)
            child_path = (*path, key)
            line_map[child_path] = value_node.start_mark.line + 1
            line_map.update(_build_line_map(value_node, child_path))
    elif isinstance(node, SequenceNode):
        for index, child_node in enumerate(node.value):
            child_path = (*path, index)
            line_map[child_path] = child_node.start_mark.line + 1
            line_map.update(_build_line_map(child_node, child_path))

    return line_map


def _closest_line(line_map: dict[tuple[Any, ...], int], path: tuple[Any, ...]) -> int:
    if path in line_map:
        return line_map[path]

    for end in range(len(path), -1, -1):
        prefix = path[:end]
        if prefix in line_map:
            return line_map[prefix]

    return 1


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _matches_type(value: Any, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "number": _is_number(value),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, True)


def _iter_schema_errors(instance: Any, schema: dict[str, Any], path: tuple[Any, ...] = ()) -> list[SchemaIssue]:
    issues: list[SchemaIssue] = []

    expected_type = schema.get("type")
    if isinstance(expected_type, str) and not _matches_type(instance, expected_type):
        issues.append(SchemaIssue(path, f"Expected type '{expected_type}'"))
        return issues

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and instance not in enum_values:
        issues.append(SchemaIssue(path, f"Value {instance!r} is not one of {enum_values}"))

    if _is_number(instance):
        minimum = schema.get("minimum")
        if isinstance(minimum, (int, float)) and instance < minimum:
            issues.append(SchemaIssue(path, f"{instance} is less than minimum {minimum}"))
        maximum = schema.get("maximum")
        if isinstance(maximum, (int, float)) and instance > maximum:
            issues.append(SchemaIssue(path, f"{instance} is greater than maximum {maximum}"))
        exclusive_minimum = schema.get("exclusiveMinimum")
        if isinstance(exclusive_minimum, (int, float)) and instance <= exclusive_minimum:
            issues.append(
                SchemaIssue(path, f"{instance} must be greater than exclusiveMinimum {exclusive_minimum}")
            )

    if isinstance(instance, str):
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(instance) < min_length:
            issues.append(SchemaIssue(path, f"String length {len(instance)} is less than minLength {min_length}"))

    if isinstance(instance, list):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(instance) < min_items:
            issues.append(SchemaIssue(path, f"Array size {len(instance)} is less than minItems {min_items}"))

        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(instance):
                issues.extend(_iter_schema_errors(item, item_schema, (*path, index)))

    if isinstance(instance, dict):
        min_properties = schema.get("minProperties")
        if isinstance(min_properties, int) and len(instance) < min_properties:
            issues.append(
                SchemaIssue(path, f"Object has {len(instance)} properties, fewer than minProperties {min_properties}")
            )

        required = schema.get("required", [])
        if isinstance(required, list):
            for required_key in required:
                if required_key not in instance:
                    issues.append(SchemaIssue(path, f"Missing required property '{required_key}'"))

        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, property_schema in properties.items():
                if key in instance and isinstance(property_schema, dict):
                    issues.extend(_iter_schema_errors(instance[key], property_schema, (*path, key)))

        additional_properties = schema.get("additionalProperties", True)
        if additional_properties is False and isinstance(properties, dict):
            allowed = set(properties.keys())
            for key in instance.keys():
                if key not in allowed:
                    issues.append(SchemaIssue((*path, key), f"Additional property '{key}' is not allowed"))
        elif isinstance(additional_properties, dict):
            known = set(properties.keys()) if isinstance(properties, dict) else set()
            for key, value in instance.items():
                if key not in known:
                    issues.extend(_iter_schema_errors(value, additional_properties, (*path, key)))

    return issues


def _validate_file(config_path: Path, schema_path: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    text = config_path.read_text(encoding="utf-8")

    try:
        parsed = yaml.safe_load(text)
        composed = yaml.compose(text)
    except yaml.YAMLError as error:
        line = 1
        if getattr(error, "problem_mark", None) is not None:
            line = error.problem_mark.line + 1
        issues.append(ValidationIssue(config_path=config_path, message=f"Parse error: {error}", line=line))
        return issues

    if parsed is None:
        parsed = {}

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        issues.append(
            ValidationIssue(
                config_path=config_path,
                message=f"Invalid schema '{schema_path}': {error.msg}",
                line=error.lineno,
            )
        )
        return issues

    line_map = _build_line_map(composed)
    for error in _iter_schema_errors(parsed, schema):
        line = _closest_line(line_map, error.path)
        display_path = "/".join(str(segment) for segment in error.path) or "<root>"
        issues.append(ValidationIssue(config_path=config_path, message=f"{display_path}: {error.message}", line=line))

    return issues


def validate_configs(
    config_dir: Path = DEFAULT_CONFIG_DIR,
    schema_dir: Path = DEFAULT_SCHEMA_DIR,
) -> tuple[list[ValidationIssue], list[Path]]:
    issues: list[ValidationIssue] = []
    skipped: list[Path] = []

    for config_path in _iter_config_files(config_dir):
        schema_path = schema_dir / _schema_name_for(config_path)
        if not schema_path.exists():
            skipped.append(config_path)
            continue
        issues.extend(_validate_file(config_path, schema_path))

    return issues, skipped


def main() -> int:
    issues, skipped = validate_configs()

    if skipped:
        print("Skipped files without matching schema:")
        for path in skipped:
            print(f"  - {path.relative_to(REPO_ROOT)}")

    if issues:
        print("\nConfiguration validation failed:")
        for issue in issues:
            rel_path = issue.config_path.relative_to(REPO_ROOT)
            print(f"  - {rel_path}:{issue.line} -> {issue.message}")
        return 1

    print("Configuration validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
