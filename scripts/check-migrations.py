#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


def main() -> int:
    migrations_dir = Path("data/migrations")
    if not migrations_dir.exists():
        print("No migrations directory found.")
        return 0

    migration_files = [
        path for path in migrations_dir.iterdir()
        if path.is_file() and path.name != "README.md"
    ]

    if not migration_files:
        print("No migration files to validate.")
        return 0

    prefixes = {}
    for path in migration_files:
        parts = path.stem.split("_", 1)
        prefix = parts[0]
        if not prefix.isdigit():
            raise SystemExit(f"Migration {path.name} must start with a numeric prefix.")
        if prefix in prefixes:
            raise SystemExit(f"Duplicate migration prefix {prefix} in {path.name} and {prefixes[prefix]}.")
        prefixes[prefix] = path.name

    print(f"Validated {len(migration_files)} migration file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
