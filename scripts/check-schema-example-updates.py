#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_ROOT = Path("data/schemas")
EXAMPLES_ROOT = Path("data/schemas/examples")


def _merge_base() -> str | None:
    for candidate in ("origin/main", "origin/master", "main", "master"):
        proc = subprocess.run(
            ["git", "merge-base", "HEAD", candidate],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    return None


def _changed_files(base: str) -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def main() -> int:
    base = _merge_base()
    if not base:
        print("Could not determine merge-base; skipping schema/example co-update enforcement.")
        return 0

    changed = set(_changed_files(base))
    changed_schema_files = {
        path for path in changed if path.startswith(f"{SCHEMAS_ROOT.as_posix()}/") and path.endswith(".schema.json")
    }
    if not changed_schema_files:
        print("No schema changes detected.")
        return 0

    changed_examples = {
        path for path in changed if path.startswith(f"{EXAMPLES_ROOT.as_posix()}/") and path.endswith(".json")
    }

    missing_examples: list[str] = []
    for schema_file in sorted(changed_schema_files):
        schema_name = Path(schema_file).name.replace(".schema.json", "")
        expected = f"{EXAMPLES_ROOT.as_posix()}/{schema_name}.json"
        if expected not in changed_examples:
            missing_examples.append(f"{schema_file} requires example update: {expected}")

    if missing_examples:
        for line in missing_examples:
            print(f"Schema/example update check failed: {line}")
        return 1

    print("Schema/example update check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
