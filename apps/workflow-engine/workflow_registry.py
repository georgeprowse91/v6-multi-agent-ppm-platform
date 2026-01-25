from pathlib import Path

WORKFLOW_DEFINITIONS_DIR = Path(__file__).resolve().parent / "workflows" / "definitions"


def list_workflow_definitions() -> list[Path]:
    return sorted(WORKFLOW_DEFINITIONS_DIR.glob("*.workflow.yaml"))
