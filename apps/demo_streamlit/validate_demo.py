from __future__ import annotations

import ast
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = Path(__file__).resolve().parent
APP_FILE = DEMO_DIR / "app.py"
SCENARIOS_FILE = REPO_ROOT / "apps/web/storage/scenarios.json"

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

BANNED_ACTIVITY_LABELS = (
    "Define scope",
    "Review dependencies",
    "Publish artifact",
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
        if ("http" + "://") in source_lower or ("https" + "://") in source_lower:
            errors.append(f"Potential external URL literal found in {file_path.name}")

    app_source = APP_FILE.read_text(encoding="utf-8")
    for label in BANNED_ACTIVITY_LABELS:
        if label in app_source:
            errors.append(f"app.py still contains prior hard-coded activity label: {label}")
    if re.search(r"(^|\n)\s*activities\s*=\s*\[", app_source):
        errors.append("app.py contains a literal fallback activity list assignment")
    if "Executed quick action" in app_source:
        errors.append("app.py still contains legacy quick action executed text")
    if "def scenario_restart" not in app_source or "assistant_step" not in app_source:
        errors.append("app.py appears to be missing restart parity logic")

    scenarios = json.loads(SCENARIOS_FILE.read_text(encoding="utf-8"))
    methodologies = scenarios.get("methodologies")
    if not isinstance(methodologies, list) or len(methodologies) == 0:
        errors.append("scenarios.json must contain at least one methodology")
    else:
        total_activities = 0
        for methodology in methodologies:
            for stage in methodology.get("stages", []):
                total_activities += len(stage.get("activities", []))
        if total_activities == 0:
            errors.append("scenarios.json must contain at least one activity")

    return errors


if __name__ == "__main__":
    issues = validate_demo()
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}")
        raise SystemExit(1)
    print("Standalone demo validation passed.")
