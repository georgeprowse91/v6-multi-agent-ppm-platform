from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = Path(__file__).resolve().parent
APP_FILE = DEMO_DIR / "app.py"

BANNED_IMPORT_SNIPPETS = (
    "fastapi",
    "httpx",
    "requests",
    "asyncpg",
    "psycopg2",
    "integrations",
    "services",
    "orchestration-service",
)

REQUIRED_DEMO_FILES = [
    "apps/web/data/projects.json",
    "apps/web/data/demo_seed.json",
    "apps/web/data/demo/demo_run_log.json",
    "apps/web/data/demo_conversations/project_intake.json",
    "apps/web/data/demo_conversations/resource_request.json",
    "apps/web/data/demo_conversations/vendor_procurement.json",
    "examples/demo-scenarios/portfolio-health.json",
    "examples/demo-scenarios/lifecycle-metrics.json",
    "examples/demo-scenarios/workflow-monitoring.json",
    "examples/demo-scenarios/approvals.json",
    "examples/demo-scenarios/assistant-responses.json",
    "apps/web/storage/scenarios.json",
    "apps/web/storage/notifications.json",
    "apps/demo_streamlit/data/feature_flags_demo.json",
]


def parse_imports(file_path: Path) -> set[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
    return imports


def validate_demo() -> list[str]:
    errors: list[str] = []

    for rel in REQUIRED_DEMO_FILES:
        if not (REPO_ROOT / rel).exists():
            errors.append(f"Missing required demo file: {rel}")

    for file_path in DEMO_DIR.glob("*.py"):
        imports = parse_imports(file_path)
        for banned in BANNED_IMPORT_SNIPPETS:
            if any(banned in name for name in imports):
                errors.append(f"Banned import detected in {file_path.name}: {banned}")

        source_lower = file_path.read_text(encoding="utf-8").lower()
        if any(f"{scheme}://" in source_lower for scheme in ("http", "https")):
            errors.append(f"Potential external URL literal found in {file_path.name}")

    app_source = APP_FILE.read_text(encoding="utf-8")
    if "Define scope" in app_source or "Review dependencies" in app_source or "Publish artifact" in app_source:
        errors.append("app.py still appears to contain the old hard-coded activity list")
    if "scenarios.json" not in app_source:
        errors.append("app.py must reference scenarios.json as the stages/activities source")
    if '"responses"' not in app_source or '"match"' not in app_source:
        errors.append("app.py must reference assistant response matching using responses/match keys")

    return errors


if __name__ == "__main__":
    issues = validate_demo()
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}")
        raise SystemExit(1)
    print("Standalone demo validation passed.")
