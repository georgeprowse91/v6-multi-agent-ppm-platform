#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = REPO_ROOT / "data" / "schemas"
EXAMPLES_DIR = SCHEMA_DIR / "examples"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def main() -> int:
    if not EXAMPLES_DIR.exists():
        raise SystemExit(f"Examples directory missing: {EXAMPLES_DIR}")

    failures: list[str] = []
    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = _load_json(schema_path)
        example_path = EXAMPLES_DIR / schema_path.name.replace(".schema.json", ".json")
        if not example_path.exists():
            failures.append(f"Missing example for {schema_path.name}")
            continue

        instance = _load_json(example_path)
        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(instance), key=lambda err: err.path)
        if errors:
            formatted = "; ".join(error.message for error in errors)
            failures.append(f"{schema_path.name}: {formatted}")

    if failures:
        for failure in failures:
            print(f"Schema validation failed: {failure}")
        return 1

    print("Schema validation succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
