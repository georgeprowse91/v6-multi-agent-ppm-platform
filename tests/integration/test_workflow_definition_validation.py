from __future__ import annotations

import sys
from pathlib import Path

WORKFLOW_SRC = Path(__file__).resolve().parents[2] / "services" / "workflow-service" / "src"
sys.path.insert(0, str(WORKFLOW_SRC))

from workflow_definitions import validate_definition  # noqa: E402


def test_validate_definition_rejects_duplicate_ids() -> None:
    definition = {
        "metadata": {"name": "Bad"},
        "steps": [
            {"id": "dup", "type": "task", "config": {"agent": "a", "action": "run"}},
            {"id": "dup", "type": "task", "config": {"agent": "a", "action": "run"}},
        ],
    }
    errors = validate_definition(definition)
    assert any("duplicate" in error for error in errors)


def test_validate_definition_requires_parallel_join() -> None:
    definition = {
        "metadata": {"name": "Bad parallel"},
        "steps": [
            {
                "id": "parallel",
                "type": "parallel",
                "branches": [{"name": "a", "next": "task-a"}],
            },
            {"id": "task-a", "type": "task", "config": {"agent": "a", "action": "run"}},
        ],
    }
    errors = validate_definition(definition)
    assert any("join" in error for error in errors)


def test_validate_definition_requires_task_config() -> None:
    definition = {
        "metadata": {"name": "Bad task"},
        "steps": [{"id": "task-a", "type": "task"}],
    }
    errors = validate_definition(definition)
    assert any("requires agent/action" in error for error in errors)
