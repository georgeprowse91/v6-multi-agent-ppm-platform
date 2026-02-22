from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

CompatibilityMode = Literal["backward", "forward", "full"]


@dataclass(frozen=True)
class CompatibilityResult:
    backward_compatible: bool
    forward_compatible: bool
    notes: list[str]


def compare_schema_versions(old: dict[str, Any], new: dict[str, Any]) -> CompatibilityResult:
    old_properties = old.get("properties", {})
    new_properties = new.get("properties", {})
    old_required = set(old.get("required", []))
    new_required = set(new.get("required", []))

    notes: list[str] = []

    removed_props = sorted(set(old_properties) - set(new_properties))
    if removed_props:
        notes.append(f"Removed properties: {', '.join(removed_props)}")

    added_required = sorted(new_required - old_required)
    if added_required:
        notes.append(f"Added required properties: {', '.join(added_required)}")

    type_changes: list[str] = []
    for prop in sorted(set(old_properties) & set(new_properties)):
        old_type = old_properties[prop].get("type")
        new_type = new_properties[prop].get("type")
        if old_type != new_type:
            type_changes.append(f"{prop}: {old_type} -> {new_type}")
    if type_changes:
        notes.append(f"Property type changes: {', '.join(type_changes)}")

    backward_compatible = not removed_props and not added_required and not type_changes

    removed_required = sorted(old_required - new_required)
    added_optional = sorted((set(new_properties) - set(old_properties)) - new_required)
    forward_breaks: list[str] = []
    if removed_required:
        forward_breaks.append(f"Removed required properties: {', '.join(removed_required)}")
    if added_optional:
        forward_breaks.append(f"Added optional properties: {', '.join(added_optional)}")
    if forward_breaks:
        notes.extend(forward_breaks)

    forward_compatible = (
        not removed_props and not type_changes and not removed_required and not added_optional
    )

    if not notes:
        notes.append("No compatibility-impacting structural changes detected")

    return CompatibilityResult(
        backward_compatible=backward_compatible,
        forward_compatible=forward_compatible,
        notes=notes,
    )


def validate_compatibility(
    old: dict[str, Any], new: dict[str, Any], mode: CompatibilityMode
) -> CompatibilityResult:
    result = compare_schema_versions(old, new)
    is_valid = {
        "backward": result.backward_compatible,
        "forward": result.forward_compatible,
        "full": result.backward_compatible and result.forward_compatible,
    }[mode]
    if not is_valid:
        detail = "; ".join(result.notes)
        raise ValueError(f"Compatibility mode '{mode}' violated: {detail}")
    return result
