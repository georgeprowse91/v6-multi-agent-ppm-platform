from __future__ import annotations

from pathlib import Path
import logging
from typing import Any, cast

from workflow_storage import WorkflowStore
from security.config import load_yaml

from jsonschema import Draft202012Validator, FormatChecker

logger = logging.getLogger(__name__)


def load_definition(path: Path, schema_path: Path) -> dict[str, Any]:
    definition = cast(dict[str, Any], load_yaml(path))
    schema = cast(dict[str, Any], load_yaml(schema_path))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(definition), key=lambda err: err.path)
    if errors:
        formatted = "; ".join(error.message for error in errors)
        raise ValueError(f"Workflow definition invalid: {formatted}")
    custom_errors = validate_definition(definition)
    if custom_errors:
        formatted = "; ".join(custom_errors)
        raise ValueError(f"Workflow definition invalid: {formatted}")
    return definition


def seed_definitions(store: WorkflowStore, definitions_dir: Path, schema_path: Path) -> None:
    if not definitions_dir.exists():
        return
    for definition_path in definitions_dir.glob("*.workflow.yaml"):
        workflow_id = definition_path.stem.replace(".workflow", "")
        if store.get_definition(workflow_id):
            continue
        try:
            definition = load_definition(definition_path, schema_path)
        except ValueError as exc:
            logger.warning("Skipping invalid workflow definition %s: %s", definition_path.name, exc)
            continue
        store.upsert_definition(workflow_id, definition)


def validate_definition(definition: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    steps = definition.get("steps") or []
    if not isinstance(steps, list) or not steps:
        errors.append("steps: must contain at least one step")
        return errors

    step_ids: set[str] = set()
    for index, step in enumerate(steps):
        step_id = step.get("id")
        if not step_id:
            errors.append(f"steps[{index}].id: is required")
            continue
        if step_id in step_ids:
            errors.append(f"steps[{index}].id: duplicate step id '{step_id}'")
        step_ids.add(step_id)

    allowed_types = {
        "task",
        "decision",
        "approval",
        "notification",
        "parallel",
        "loop",
        "api",
        "script",
    }
    for index, step in enumerate(steps):
        step_id = step.get("id", f"steps[{index}]")
        step_type = step.get("type")
        if step_type not in allowed_types:
            errors.append(f"steps[{index}].type: unsupported type '{step_type}'")
            continue

        if step_type == "parallel":
            branches = step.get("branches") or []
            if not branches:
                errors.append(f"steps[{index}].branches: parallel step '{step_id}' requires branches")
            join = step.get("join")
            if not join:
                errors.append(f"steps[{index}].join: parallel step '{step_id}' requires join")
            for branch_index, branch in enumerate(branches):
                target = branch.get("next")
                if target and target not in step_ids:
                    errors.append(
                        f"steps[{index}].branches[{branch_index}].next: unknown step '{target}'"
                    )
            if join and join not in step_ids:
                errors.append(f"steps[{index}].join: unknown step '{join}'")

        if step_type == "loop":
            condition = step.get("condition")
            if not condition:
                errors.append(f"steps[{index}].condition: loop step '{step_id}' requires condition")
            next_step = step.get("next")
            exit_step = step.get("exit")
            if not next_step and not exit_step:
                errors.append(f"steps[{index}]: loop step '{step_id}' needs next or exit")
            if next_step and next_step not in step_ids:
                errors.append(f"steps[{index}].next: unknown step '{next_step}'")
            if exit_step and exit_step not in step_ids:
                errors.append(f"steps[{index}].exit: unknown step '{exit_step}'")

        next_step = step.get("next")
        if next_step and step_type not in {"parallel", "loop"}:
            if isinstance(next_step, list):
                for target in next_step:
                    if target not in step_ids:
                        errors.append(f"steps[{index}].next: unknown step '{target}'")
            elif next_step not in step_ids:
                errors.append(f"steps[{index}].next: unknown step '{next_step}'")

        default_next = step.get("default_next")
        if default_next and default_next not in step_ids:
            errors.append(f"steps[{index}].default_next: unknown step '{default_next}'")

        branches = step.get("branches") or []
        for branch_index, branch in enumerate(branches):
            target = branch.get("next")
            if target and target not in step_ids:
                errors.append(
                    f"steps[{index}].branches[{branch_index}].next: unknown step '{target}'"
                )

        if step_type in {"task", "api"}:
            config = step.get("config") or {}
            has_agent = bool(config.get("agent") and config.get("action"))
            has_endpoint = bool(config.get("endpoint"))
            if not has_agent and not has_endpoint:
                errors.append(
                    f"steps[{index}].config: task '{step_id}' requires agent/action or endpoint"
                )

    edges: list[tuple[str, str]] = []
    for step in steps:
        step_id = step.get("id")
        if not step_id:
            continue
        next_step = step.get("next")
        if isinstance(next_step, list):
            edges.extend((step_id, target) for target in next_step if target)
        elif next_step:
            edges.append((step_id, next_step))
        default_next = step.get("default_next")
        if default_next:
            edges.append((step_id, default_next))
        for branch in step.get("branches") or []:
            target = branch.get("next")
            if target:
                edges.append((step_id, target))
        join = step.get("join")
        if join:
            edges.append((step_id, join))
        exit_step = step.get("exit")
        if exit_step:
            edges.append((step_id, exit_step))

    if _has_cycle(step_ids, edges):
        errors.append("workflow: graph contains a cycle")

    return errors


def _has_cycle(step_ids: set[str], edges: list[tuple[str, str]]) -> bool:
    adjacency: dict[str, list[str]] = {step_id: [] for step_id in step_ids}
    for source, target in edges:
        if source in adjacency and target in adjacency:
            adjacency[source].append(target)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(step_id: str) -> bool:
        if step_id in visiting:
            return True
        if step_id in visited:
            return False
        visiting.add(step_id)
        for neighbor in adjacency.get(step_id, []):
            if visit(neighbor):
                return True
        visiting.remove(step_id)
        visited.add(step_id)
        return False

    return any(visit(step_id) for step_id in step_ids)
