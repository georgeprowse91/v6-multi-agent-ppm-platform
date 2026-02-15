from __future__ import annotations

import ast
from pathlib import Path

APP_PATH = Path(__file__).resolve().parent / "app.py"
REPO_ROOT = APP_PATH.resolve().parents[2]

BANNED_IMPORT_SNIPPETS = ("asyncpg", "psycopg2", "orchestration-service", "integrations")
REQUIRED_DEMO_FILES = [
    "apps/web/data/projects.json",
    "apps/web/data/demo_seed.json",
    "apps/web/data/demo/demo_run_log.json",
    "examples/demo-scenarios/portfolio-health.json",
    "examples/demo-scenarios/schedule.json",
    "examples/demo-scenarios/wbs.json",
    "examples/demo-scenarios/approvals.json",
    "examples/demo-scenarios/assistant-responses.json",
    "apps/web/data/demo_conversations/project_intake.json",
    "apps/web/data/demo_dashboards/project-dashboard-health.json",
    "apps/web/data/demo_dashboards/project-dashboard-risks.json",
    "apps/web/data/demo_dashboards/project-dashboard-issues.json",
    "apps/web/data/demo_dashboards/project-dashboard-narrative.json",
    "apps/web/storage/scenarios.json",
    "apps/web/storage/notifications.json",
]


def validate_demo() -> list[str]:
    source = APP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    errors: list[str] = []

    for rel in REQUIRED_DEMO_FILES:
        if not (REPO_ROOT / rel).exists():
            errors.append(f"Missing required demo file: {rel}")

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")

    for banned in BANNED_IMPORT_SNIPPETS:
        if any(banned in name for name in imports):
            errors.append(f"Banned import detected: {banned}")

    lower_source = source.lower()
    if "http://" in lower_source or "https://" in lower_source:
        errors.append("Potential external HTTP URL found in app.py")

    return errors


if __name__ == "__main__":
    issues = validate_demo()
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}")
        raise SystemExit(1)
    print("Standalone demo validation passed.")
