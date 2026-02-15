from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = Path(__file__).resolve().parent
ASSISTANT_PANEL = REPO_ROOT / "apps/web/frontend/src/components/assistant/AssistantPanel.tsx"

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
    "apps/demo_streamlit/data/assistant_outcome_variants.json",
]

EXPECTED_SCENARIOS = ["project_intake", "resource_request", "vendor_procurement"]


def parse_imports(file_path: Path) -> set[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
    return imports


def validate_react_scenarios() -> list[str]:
    source = ASSISTANT_PANEL.read_text(encoding="utf-8")
    found = re.findall(r"id:\s*'([a-z_]+)'", source)
    assistant_scenarios = sorted({value for value in found if value in EXPECTED_SCENARIOS})
    if assistant_scenarios != sorted(EXPECTED_SCENARIOS):
        return [f"React DEMO_SCENARIOS mismatch. Expected {EXPECTED_SCENARIOS}, found {assistant_scenarios}"]
    return []


def validate_demo() -> list[str]:
    errors: list[str] = []

    for rel in REQUIRED_DEMO_FILES:
        if not (REPO_ROOT / rel).exists():
            errors.append(f"Missing required demo file: {rel}")

    python_files = list(DEMO_DIR.glob("*.py"))
    for file_path in python_files:
        imports = parse_imports(file_path)
        for banned in BANNED_IMPORT_SNIPPETS:
            if any(banned in name for name in imports):
                errors.append(f"Banned import detected in {file_path.name}: {banned}")

        source_lower = file_path.read_text(encoding="utf-8").lower()
        if any(f"{scheme}://" in source_lower for scheme in ("http", "https")):
            errors.append(f"Potential external URL literal found in {file_path.name}")

    errors.extend(validate_react_scenarios())

    return errors


if __name__ == "__main__":
    issues = validate_demo()
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}")
        raise SystemExit(1)
    print("Standalone demo validation passed.")
