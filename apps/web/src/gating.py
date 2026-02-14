from __future__ import annotations

from typing import Any

from methodologies import get_methodology_map
from workspace_state import WorkspaceState


def _resolve_methodology_map(
    methodology_map: dict[str, Any] | None, methodology_id: str | None
) -> dict[str, Any]:
    if methodology_map is None:
        return get_methodology_map(methodology_id)
    return methodology_map


def _iter_activity_tree(activities: list[dict[str, Any]], stage: dict[str, Any] | None):
    for activity in activities:
        yield activity, stage
        children = activity.get("children", []) or []
        yield from _iter_activity_tree(children, stage)


def _iter_methodology_activities(methodology_map: dict[str, Any]):
    for stage in methodology_map.get("stages", []):
        yield from _iter_activity_tree(stage.get("activities", []) or [], stage)


def _iter_all_activities(methodology_map: dict[str, Any]):
    for activity, stage in _iter_methodology_activities(methodology_map):
        yield activity, stage
    for activity in methodology_map.get("monitoring", []):
        yield activity, None


def _activity_lookup(methodology_map: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for activity, _stage in _iter_all_activities(methodology_map):
        lookup[activity["id"]] = activity
    return lookup


def _missing_prereqs(activity: dict[str, Any], state: WorkspaceState) -> list[str]:
    return [
        prereq
        for prereq in activity.get("prerequisites", [])
        if not state.activity_completion.get(prereq)
    ]


def evaluate_activity_access(
    methodology_map: dict[str, Any] | None,
    state: WorkspaceState,
    activity_id: str,
    methodology_id: str | None = None,
) -> dict[str, Any]:
    methodology_map = _resolve_methodology_map(methodology_map, methodology_id)
    lookup = _activity_lookup(methodology_map)
    activity = lookup.get(activity_id)
    if not activity:
        return {
            "allowed": False,
            "reasons": ["Unknown activity."],
            "missing_prereqs": [],
        }
    if activity.get("category") == "monitoring":
        return {"allowed": True, "reasons": [], "missing_prereqs": []}
    missing = _missing_prereqs(activity, state)
    if missing:
        return {
            "allowed": False,
            "reasons": ["Complete prerequisites to unlock this activity."],
            "missing_prereqs": missing,
        }
    return {"allowed": True, "reasons": [], "missing_prereqs": []}


def next_required_activity(
    methodology_map: dict[str, Any] | None,
    state: WorkspaceState,
    methodology_id: str | None = None,
) -> str | None:
    methodology_map = _resolve_methodology_map(methodology_map, methodology_id)
    if not state.current_activity_id and not state.current_stage_id:
        return None

    lookup = _activity_lookup(methodology_map)

    if state.current_activity_id:
        activity = lookup.get(state.current_activity_id)
        if activity:
            missing = _missing_prereqs(activity, state)
            if missing:
                return missing[0]

    if state.current_stage_id:
        stage = next(
            (
                item
                for item in methodology_map.get("stages", [])
                if item.get("id") == state.current_stage_id
            ),
            None,
        )
        if stage:
            for activity in stage.get("activities", []):
                if not state.activity_completion.get(activity["id"], False):
                    missing = _missing_prereqs(activity, state)
                    if missing:
                        return missing[0]

    return None


def stage_progress(
    methodology_map: dict[str, Any] | None,
    state: WorkspaceState,
    stage_id: str,
    methodology_id: str | None = None,
) -> dict[str, Any]:
    methodology_map = _resolve_methodology_map(methodology_map, methodology_id)
    stage = next(
        (item for item in methodology_map.get("stages", []) if item.get("id") == stage_id),
        None,
    )
    if not stage:
        return {"complete_count": 0, "total_count": 0, "percent": 0.0}

    activities = [activity for activity, _stage in _iter_activity_tree(stage.get("activities", []) or [], stage)]
    total_count = len(activities)
    complete_count = sum(
        1 for activity in activities if state.activity_completion.get(activity["id"], False)
    )
    percent = round((complete_count / total_count) * 100, 1) if total_count else 0.0

    return {
        "complete_count": complete_count,
        "total_count": total_count,
        "percent": percent,
    }
