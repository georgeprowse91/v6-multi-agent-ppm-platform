"""
Stateless utility helpers extracted from WorkflowEngineAgent.

These functions are pure or near-pure and do not require access to the
agent instance.  The main agent class and action handlers import them
rather than carrying their own copies.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree

from workflow_spec import load_workflow_spec, parse_workflow_spec

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------


async def generate_workflow_id() -> str:
    """Generate unique workflow ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"WF-{timestamp}"


async def generate_instance_id() -> str:
    """Generate unique instance ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"INST-{timestamp}"


# ---------------------------------------------------------------------------
# Workflow definition helpers
# ---------------------------------------------------------------------------


def normalize_workflow_definition(workflow_config: dict[str, Any]) -> dict[str, Any]:
    if "workflow_spec" in workflow_config:
        spec = load_workflow_spec(workflow_config["workflow_spec"])
        workflow_config = {**workflow_config, **spec}
    if "workflow_yaml" in workflow_config:
        spec = load_workflow_spec(workflow_config["workflow_yaml"])
        workflow_config = {**workflow_config, **spec}
    metadata = workflow_config.get("metadata") or {}
    if metadata:
        workflow_config.setdefault("name", metadata.get("name"))
        workflow_config.setdefault("description", metadata.get("description"))
        workflow_config.setdefault("version", metadata.get("version"))
        workflow_config.setdefault("owner", metadata.get("owner"))
    return workflow_config


async def validate_workflow_definition(
    workflow_config: dict[str, Any],
) -> dict[str, Any]:
    """Validate workflow definition."""
    errors = []

    if not workflow_config.get("name"):
        errors.append("Workflow name is required")

    if (
        not workflow_config.get("tasks")
        and not workflow_config.get("steps")
        and not workflow_config.get("bpmn_xml")
    ):
        errors.append("Workflow must have at least one task")

    return {"valid": len(errors) == 0, "errors": errors}


async def parse_workflow_definition(workflow_config: dict[str, Any]) -> dict[str, Any]:
    """Parse workflow definition."""
    bpmn_xml = workflow_config.get("bpmn_xml")
    if bpmn_xml:
        return parse_bpmn_xml(bpmn_xml)
    if workflow_config.get("steps"):
        parsed = parse_workflow_spec(workflow_config)
        return {
            "tasks": parsed.tasks,
            "events": workflow_config.get("events", []),
            "gateways": workflow_config.get("gateways", []),
            "transitions": parsed.transitions,
            "dependencies": parsed.dependencies,
        }
    return {
        "tasks": workflow_config.get("tasks", []),
        "events": workflow_config.get("events", []),
        "gateways": workflow_config.get("gateways", []),
        "transitions": workflow_config.get("transitions", []),
        "dependencies": workflow_config.get("dependencies", {}),
    }


# ---------------------------------------------------------------------------
# BPMN parsing
# ---------------------------------------------------------------------------


def parse_bpmn_xml(bpmn_xml: str) -> dict[str, Any]:
    """Parse BPMN 2.0 XML into workflow tasks and transitions."""
    parsed = _parse_bpmn_with_bpmn_python(bpmn_xml)
    if parsed:
        return parsed
    root = ElementTree.fromstring(bpmn_xml)
    namespace = {"bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL"}

    def _findall(tag: str) -> list[ElementTree.Element]:
        return root.findall(f".//bpmn:{tag}", namespaces=namespace)

    tasks: list[dict[str, Any]] = []
    transitions: list[dict[str, Any]] = []

    start_events = {event.get("id") for event in _findall("startEvent") if event.get("id")}

    for task_type, internal_type in [
        ("userTask", "human"),
        ("serviceTask", "automated"),
        ("scriptTask", "automated"),
        ("task", "automated"),
    ]:
        for task in _findall(task_type):
            task_id = task.get("id")
            if not task_id:
                continue
            tasks.append(
                {
                    "task_id": task_id,
                    "name": task.get("name"),
                    "type": internal_type,
                    "initial": False,
                }
            )

    for flow in _findall("sequenceFlow"):
        source = flow.get("sourceRef")
        target = flow.get("targetRef")
        if source and target:
            transitions.append({"source": source, "target": target})

    initial_targets = {
        flow.get("targetRef")
        for flow in _findall("sequenceFlow")
        if flow.get("sourceRef") in start_events
    }
    for task in tasks:
        if task.get("task_id") in initial_targets:
            task["initial"] = True

    dependencies: dict[str, list[str]] = {}
    incoming: dict[str, set[str]] = {}
    for transition in transitions:
        source = transition.get("source")
        target = transition.get("target")
        if source and target:
            incoming.setdefault(target, set()).add(source)
    for task_id, deps in incoming.items():
        dependencies[task_id] = sorted(deps)
    return {
        "tasks": tasks,
        "events": [],
        "gateways": [],
        "transitions": transitions,
        "dependencies": dependencies,
    }


def _parse_bpmn_with_bpmn_python(bpmn_xml: str) -> dict[str, Any] | None:
    spec = importlib.util.find_spec("bpmn_python")
    if not spec:
        return None
    bpmn_diagram_rep = importlib.import_module("bpmn_python.bpmn_diagram_rep")
    if not hasattr(bpmn_diagram_rep, "BpmnDiagramGraph"):
        return None
    diagram = bpmn_diagram_rep.BpmnDiagramGraph()
    if hasattr(diagram, "load_diagram_from_xml_string"):
        diagram.load_diagram_from_xml_string(bpmn_xml)
    else:
        return None
    tasks = []
    for node_id, node in diagram.diagram_graph.nodes.items():
        node_type = node[1].get("type")
        if node_type in {"userTask", "serviceTask", "scriptTask", "task"}:
            tasks.append(
                {
                    "task_id": node_id,
                    "name": node[1].get("name"),
                    "type": "human" if node_type == "userTask" else "automated",
                    "initial": False,
                }
            )
    transitions = [{"source": edge[0], "target": edge[1]} for edge in diagram.diagram_graph.edges]
    incoming: dict[str, set[str]] = {}
    for transition in transitions:
        source = transition.get("source")
        target = transition.get("target")
        if source and target:
            incoming.setdefault(target, set()).add(source)
    dependencies = {task_id: sorted(deps) for task_id, deps in incoming.items()}
    return {
        "tasks": tasks,
        "events": [],
        "gateways": [],
        "transitions": transitions,
        "dependencies": dependencies,
    }


# ---------------------------------------------------------------------------
# Durable orchestration builder
# ---------------------------------------------------------------------------


def build_durable_orchestration(
    workflow_id: str,
    tasks: list[dict[str, Any]],
    transitions: list[dict[str, Any]],
    source: str,
) -> dict[str, Any]:
    transition_map: dict[str, list[str]] = {}
    for transition in transitions:
        source_id = transition.get("source")
        target_id = transition.get("target")
        if not source_id or not target_id:
            continue
        transition_map.setdefault(source_id, []).append(target_id)

    steps = []
    for index, task in enumerate(tasks):
        task_id = task.get("task_id")
        if not task_id:
            continue
        next_tasks = transition_map.get(task_id)
        if not next_tasks and index + 1 < len(tasks):
            next_tasks = [tasks[index + 1].get("task_id")]
        steps.append(
            {
                "step_id": f"{workflow_id}:{task_id}",
                "task_id": task_id,
                "name": task.get("name"),
                "type": task.get("type"),
                "retry_policy": task.get("retry_policy"),
                "compensation_task_id": task.get("compensation_task_id"),
                "next": [target for target in (next_tasks or []) if target],
            }
        )

    return {
        "workflow_id": workflow_id,
        "engine": "azure_durable_functions",
        "source": source,
        "steps": steps,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Condition / expression evaluation
# ---------------------------------------------------------------------------


def evaluate_condition(condition: dict[str, Any], variables: dict[str, Any]) -> bool:
    field = condition.get("field")
    operator = condition.get("operator")
    value = condition.get("value")
    resolved = resolve_reference(field, variables)

    if operator == "exists":
        return resolved is not None
    if operator == "equals":
        return resolved == value
    if operator == "not_equals":
        return resolved != value
    if operator == "greater_than":
        return resolved is not None and resolved > value
    if operator == "less_than":
        return resolved is not None and resolved < value
    if operator == "contains":
        if isinstance(resolved, (list, tuple, set)):
            return value in resolved
        if isinstance(resolved, str):
            return str(value) in resolved
    return False


def resolve_reference(value: Any, variables: dict[str, Any]) -> Any:
    if not isinstance(value, str):
        return value
    if not value.startswith("$."):
        return value
    path = value[2:].split(".")
    current: Any = {"vars": variables}
    for part in path:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


# ---------------------------------------------------------------------------
# Event criteria matching
# ---------------------------------------------------------------------------


async def event_matches_criteria(event_data: dict[str, Any], criteria: dict[str, Any]) -> bool:
    """Check if event matches subscription criteria."""
    if not criteria:
        return True

    if not isinstance(criteria, dict):
        logger.warning(
            "Invalid event criteria definition: expected object", extra={"criteria": criteria}
        )
        return False

    for field_path, condition in criteria.items():
        exists, actual_value = extract_field_path(event_data, field_path)
        if not evaluate_criterion(field_path, exists, actual_value, condition):
            return False

    return True


def extract_field_path(payload: dict[str, Any], field_path: str) -> tuple[bool, Any]:
    """Resolve dotted field paths from event payloads (for example metadata.tenant_id)."""
    if not field_path:
        return False, None

    current: Any = payload
    for segment in field_path.split("."):
        if isinstance(current, dict) and segment in current:
            current = current[segment]
            continue
        if isinstance(current, list) and segment.isdigit():
            index = int(segment)
            if 0 <= index < len(current):
                current = current[index]
                continue
        return False, None

    return True, current


def evaluate_criterion(field_path: str, exists: bool, actual_value: Any, condition: Any) -> bool:
    if isinstance(condition, dict):
        for operator, expected_value in condition.items():
            if not evaluate_operator(field_path, operator, expected_value, exists, actual_value):
                return False
        return True

    if not exists:
        return False
    return actual_value == condition


def evaluate_operator(
    field_path: str,
    operator: str,
    expected_value: Any,
    exists: bool,
    actual_value: Any,
) -> bool:
    if operator == "exists":
        if not isinstance(expected_value, bool):
            logger.warning(
                "Invalid exists operator value",
                extra={"field": field_path, "expected": expected_value},
            )
            return False
        return exists == expected_value

    if not exists:
        return False

    if operator == "eq":
        return actual_value == expected_value
    if operator == "ne":
        return actual_value != expected_value

    if operator == "in":
        if not isinstance(expected_value, list):
            logger.warning(
                "Invalid in operator value",
                extra={"field": field_path, "expected": expected_value},
            )
            return False
        if isinstance(actual_value, list):
            return any(item in expected_value for item in actual_value)
        return actual_value in expected_value

    if operator == "not_in":
        if not isinstance(expected_value, list):
            logger.warning(
                "Invalid not_in operator value",
                extra={"field": field_path, "expected": expected_value},
            )
            return False
        if isinstance(actual_value, list):
            return all(item not in expected_value for item in actual_value)
        return actual_value not in expected_value

    if operator in {"gt", "gte", "lt", "lte"}:
        compared = coerce_comparable(actual_value, expected_value)
        if compared is None:
            logger.warning(
                "Invalid comparison criterion",
                extra={
                    "field": field_path,
                    "operator": operator,
                    "actual": actual_value,
                    "expected": expected_value,
                },
            )
            return False
        left, right = compared
        if operator == "gt":
            return left > right
        if operator == "gte":
            return left >= right
        if operator == "lt":
            return left < right
        return left <= right

    logger.warning(
        "Unsupported criteria operator", extra={"field": field_path, "operator": operator}
    )
    return False


def coerce_comparable(actual_value: Any, expected_value: Any) -> tuple[Any, Any] | None:
    actual_dt = parse_datetime(actual_value)
    expected_dt = parse_datetime(expected_value)
    if actual_dt and expected_dt:
        return actual_dt, expected_dt

    actual_num = parse_number(actual_value)
    expected_num = parse_number(expected_value)
    if actual_num is not None and expected_num is not None:
        return actual_num, expected_num

    return None


def parse_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    if not isinstance(value, str):
        return None

    candidate = value.strip()
    if not candidate:
        return None

    if candidate.endswith("Z"):
        candidate = f"{candidate[:-1]}+00:00"

    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None

    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Instance filter matching
# ---------------------------------------------------------------------------


async def matches_instance_filters(instance: dict[str, Any], filters: dict[str, Any]) -> bool:
    """Check if instance matches filters."""
    if "status" in filters and instance.get("status") != filters["status"]:
        return False

    if "workflow_id" in filters and instance.get("workflow_id") != filters["workflow_id"]:
        return False

    return True
