#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "data" / "schemas"
MODELS_PATH = REPO_ROOT / "data" / "migrations" / "models.py"
MIGRATIONS_DIR = REPO_ROOT / "data" / "migrations" / "versions"

REGISTRY_TABLES = {"schema_registry", "schema_promotions", "canonical_entities"}
SCHEMA_TABLE_EXCLUSIONS = {"agent-run", "scenario"}


def _schema_name_to_table(schema_name: str) -> str:
    snake = schema_name.replace("-", "_")
    if snake.endswith("y"):
        return f"{snake[:-1]}ies"
    if snake.endswith("s"):
        return snake
    return f"{snake}s"


def _load_schema_names() -> set[str]:
    names: set[str] = set()
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        payload = json.loads(path.read_text())
        metadata = payload.get("x-schema-metadata", {})
        names.add(metadata.get("name") or path.name.replace(".schema.json", ""))
    return names


def _load_model_tables() -> set[str]:
    source = MODELS_PATH.read_text()
    tree = ast.parse(source)
    tables: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            if not isinstance(stmt, ast.Assign):
                continue
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "__tablename__":
                    if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                        tables.add(stmt.value.value)
    return tables


def _load_migration_sources() -> str:
    return "\n".join(path.read_text() for path in sorted(MIGRATIONS_DIR.glob("*.py")))


def main() -> int:
    schema_names = _load_schema_names()
    model_tables = _load_model_tables()
    migration_source = _load_migration_sources()

    expected_tables = {
        _schema_name_to_table(schema_name)
        for schema_name in schema_names
        if schema_name not in SCHEMA_TABLE_EXCLUSIONS
    }

    missing_model_tables = sorted(expected_tables - model_tables)
    missing_registry_models = sorted(REGISTRY_TABLES - model_tables)

    missing_registry_migrations = sorted(
        table for table in REGISTRY_TABLES if f'"{table}"' not in migration_source
    )

    failures: list[str] = []
    if missing_model_tables:
        failures.append(
            "Missing ORM table mappings for schemas: "
            + ", ".join(missing_model_tables)
        )
    if missing_registry_models:
        failures.append(
            "Missing schema registry model tables: " + ", ".join(missing_registry_models)
        )
    if missing_registry_migrations:
        failures.append(
            "Missing migration coverage for schema registry tables: "
            + ", ".join(missing_registry_migrations)
        )

    if failures:
        for failure in failures:
            print(f"Consistency validation failed: {failure}")
        return 1

    print("Migration/schema registry consistency validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
