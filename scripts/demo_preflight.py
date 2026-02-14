#!/usr/bin/env python3
"""Basic demo data preflight checks for data/demo/*.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ENTITY_FILES = [
    "portfolios",
    "programs",
    "projects",
    "tasks",
    "resources",
    "budgets",
    "epics",
    "sprints",
    "risks",
    "issues",
    "vendors",
    "contracts",
    "policies",
    "approvals",
    "notifications",
]


class PreflightError(Exception):
    pass


def load_rows(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise PreflightError(f"{path.name} must contain a JSON array")
    for idx, row in enumerate(data):
        if not isinstance(row, dict):
            raise PreflightError(f"{path.name}[{idx}] is not an object")
    return data


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    demo_dir = repo_root / "data" / "demo"

    if not demo_dir.exists():
        raise PreflightError(f"Demo directory does not exist: {demo_dir}")

    entities: dict[str, list[dict[str, Any]]] = {}
    for name in ENTITY_FILES:
        path = demo_dir / f"{name}.json"
        if not path.exists():
            raise PreflightError(f"Missing demo data file: {path}")
        entities[name] = load_rows(path)

    print("Demo preflight: entity counts")
    for name in ENTITY_FILES:
        print(f"  - {name}: {len(entities[name])}")

    failures: list[str] = []

    for entity_name, rows in entities.items():
        if not rows:
            failures.append(f"{entity_name}.json is empty")
        for idx, row in enumerate(rows):
            if "tenant_id" in row and not row.get("tenant_id"):
                failures.append(f"{entity_name}[{idx}] has empty tenant_id")
            if not row.get("id"):
                failures.append(f"{entity_name}[{idx}] missing id")

    portfolio_ids = {row["id"] for row in entities["portfolios"] if row.get("id")}
    program_ids = {row["id"] for row in entities["programs"] if row.get("id")}
    project_ids = {row["id"] for row in entities["projects"] if row.get("id")}

    for idx, row in enumerate(entities["programs"]):
        portfolio_id = row.get("portfolio_id")
        if portfolio_id and portfolio_id not in portfolio_ids:
            failures.append(f"programs[{idx}] has unknown portfolio_id={portfolio_id}")

    for idx, row in enumerate(entities["projects"]):
        program_id = row.get("program_id")
        if program_id and program_id not in program_ids:
            failures.append(f"projects[{idx}] has unknown program_id={program_id}")

    for idx, row in enumerate(entities["tasks"]):
        project_id = row.get("project_id")
        if project_id and project_id not in project_ids:
            failures.append(f"tasks[{idx}] has unknown project_id={project_id}")

    for idx, row in enumerate(entities["risks"]):
        project_id = row.get("project_id")
        if project_id and project_id not in project_ids:
            failures.append(f"risks[{idx}] has unknown project_id={project_id}")

    for idx, row in enumerate(entities["issues"]):
        project_id = row.get("project_id")
        if project_id and project_id not in project_ids:
            failures.append(f"issues[{idx}] has unknown project_id={project_id}")

    if failures:
        print("\nPreflight checks failed:")
        for message in failures:
            print(f"  - {message}")
        return 1

    print("\nPreflight checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PreflightError as exc:
        print(f"Preflight checks failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
