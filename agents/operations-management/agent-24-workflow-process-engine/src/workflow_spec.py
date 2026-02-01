from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml


SUPPORTED_API_VERSION = "ppm.workflow/v1"


class WorkflowSpecError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedWorkflow:
    metadata: dict[str, Any]
    tasks: list[dict[str, Any]]
    transitions: list[dict[str, Any]]
    dependencies: dict[str, list[str]]


def load_workflow_spec(payload: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload, str):
        return yaml.safe_load(payload) or {}
    return payload


def parse_workflow_spec(payload: dict[str, Any]) -> ParsedWorkflow:
    if not payload:
        raise WorkflowSpecError("Workflow specification payload is empty")

    if payload.get("apiVersion") and payload.get("apiVersion") != SUPPORTED_API_VERSION:
        raise WorkflowSpecError(f"Unsupported apiVersion {payload.get('apiVersion')}")

    metadata = payload.get("metadata", {})
    steps = payload.get("steps") or []
    if not steps:
        raise WorkflowSpecError("Workflow specification must include at least one step")

    tasks: list[dict[str, Any]] = []
    transitions: list[dict[str, Any]] = []

    for index, step in enumerate(steps):
        step_id = step.get("id")
        step_type = step.get("type", "task")
        if not step_id:
            raise WorkflowSpecError("Each step must include an id")
        if step_type in {"task", "human", "automated", "approval", "notification", "script"}:
            tasks.append(
                {
                    "task_id": step_id,
                    "name": step.get("name"),
                    "type": _map_task_type(step_type, step.get("task_type")),
                    "initial": step.get("initial", index == 0),
                    "retry_policy": _normalize_retry(step.get("retry", {})),
                    "compensation_task_id": step.get("compensation_task_id"),
                    "config": step.get("config", {}),
                    "callable": step.get("callable") or step.get("config", {}).get("callable"),
                    "script": step.get("script"),
                }
            )
        else:
            tasks.append(
                {
                    "task_id": step_id,
                    "name": step.get("name"),
                    "type": step_type,
                    "initial": step.get("initial", False),
                    "config": step.get("config", {}),
                }
            )

        transitions.extend(_parse_step_transitions(step, steps))

    dependencies = _build_dependencies(transitions)
    return ParsedWorkflow(metadata=metadata, tasks=tasks, transitions=transitions, dependencies=dependencies)


def _map_task_type(step_type: str, explicit_type: str | None) -> str:
    if explicit_type:
        return explicit_type
    if step_type in {"human", "approval"}:
        return "human"
    if step_type == "notification":
        return "logic_app"
    return "automated"


def _normalize_retry(retry: dict[str, Any]) -> dict[str, Any]:
    if not retry:
        return {}
    return {
        "max_attempts": int(retry.get("max_attempts", retry.get("maxAttempts", 1))),
        "backoff_seconds": int(retry.get("backoff_seconds", retry.get("delay_seconds", 0))),
    }


def _parse_step_transitions(step: dict[str, Any], steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    step_id = step.get("id")
    if not step_id:
        return []
    step_type = step.get("type", "task")
    transitions: list[dict[str, Any]] = []

    if step_type in {"decision", "loop"}:
        branches = step.get("branches", [])
        for branch in branches:
            transitions.append(
                {
                    "source": step_id,
                    "target": branch.get("next"),
                    "condition": branch.get("condition"),
                    "name": branch.get("name"),
                }
            )
        default_next = step.get("default_next") or step.get("next") or step.get("exit")
        if default_next:
            transitions.append({"source": step_id, "target": default_next})
        return transitions

    if step_type == "parallel":
        branches = step.get("branches", [])
        for branch in branches:
            transitions.append(
                {
                    "source": step_id,
                    "target": branch.get("next"),
                    "name": branch.get("name"),
                }
            )
        return transitions

    next_step = step.get("next")
    if isinstance(next_step, list):
        for target in next_step:
            transitions.append({"source": step_id, "target": target})
    elif next_step:
        transitions.append({"source": step_id, "target": next_step})
    else:
        index = next((i for i, candidate in enumerate(steps) if candidate.get("id") == step_id), -1)
        if index >= 0 and index + 1 < len(steps):
            transitions.append({"source": step_id, "target": steps[index + 1].get("id")})
    return transitions


def _build_dependencies(transitions: list[dict[str, Any]]) -> dict[str, list[str]]:
    incoming: dict[str, set[str]] = {}
    for transition in transitions:
        source = transition.get("source")
        target = transition.get("target")
        if not source or not target:
            continue
        incoming.setdefault(target, set()).add(source)
    return {task_id: sorted(list(deps)) for task_id, deps in incoming.items()}
