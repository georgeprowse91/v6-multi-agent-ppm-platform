from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

CompatibilityMode = Literal["backward", "forward", "full"]
ChangeType = Literal["patch", "minor", "major"]


@dataclass(frozen=True)
class SchemaMetadata:
    name: str
    version: str
    compatibility_mode: CompatibilityMode


@dataclass(frozen=True)
class SchemaRecord:
    path: Path
    schema: dict[str, Any]
    metadata: SchemaMetadata


DEFAULT_SCHEMA_ROOTS = [
    "data/schemas",
    "ops/schemas",
    "apps/workflow-service/workflows/schema",
    "apps/analytics-service/jobs/schema",
    "agents/runtime/prompts/schema",
]


class SchemaRegistry:
    def __init__(self, repo_root: Path, roots: list[str] | None = None) -> None:
        self.repo_root = repo_root
        configured_roots = roots or DEFAULT_SCHEMA_ROOTS
        self.roots = [repo_root / root for root in configured_roots]

    def iter_schemas(self) -> list[SchemaRecord]:
        records: list[SchemaRecord] = []
        for root in self.roots:
            if not root.exists():
                continue
            for schema_path in sorted(root.rglob("*.schema.json")):
                schema = json.loads(schema_path.read_text())
                metadata_raw = schema.get("x-schema-metadata", {})
                name = metadata_raw.get("name") or schema_path.name.replace(".schema.json", "")
                version = metadata_raw.get("version", "1.0.0")
                mode = metadata_raw.get("compatibility_mode", "full")
                if mode not in {"backward", "forward", "full"}:
                    raise ValueError(f"Invalid compatibility mode {mode!r} in {schema_path}")
                records.append(
                    SchemaRecord(
                        path=schema_path,
                        schema=schema,
                        metadata=SchemaMetadata(name=name, version=version, compatibility_mode=mode),
                    )
                )
        return records


@dataclass(frozen=True)
class CompatibilityResult:
    change_type: ChangeType
    backward_compatible: bool
    forward_compatible: bool
    notes: list[str]


SEMVER_ORDER = {"patch": 0, "minor": 1, "major": 2}


def compare_schemas(old: dict[str, Any], new: dict[str, Any]) -> CompatibilityResult:
    old_properties = old.get("properties", {})
    new_properties = new.get("properties", {})
    old_required = set(old.get("required", []))
    new_required = set(new.get("required", []))

    notes: list[str] = []
    severity: ChangeType = "patch"

    removed_props = sorted(set(old_properties) - set(new_properties))
    if removed_props:
        notes.append(f"Removed properties: {', '.join(removed_props)}")
        severity = "major"

    removed_required = sorted(old_required - new_required)
    if removed_required and severity != "major":
        notes.append(f"Removed required fields: {', '.join(removed_required)}")
        severity = "minor"

    added_required = sorted(new_required - old_required)
    if added_required:
        notes.append(f"Added required fields: {', '.join(added_required)}")
        severity = "major"

    added_optional = sorted((set(new_properties) - set(old_properties)) - new_required)
    if added_optional and severity == "patch":
        notes.append(f"Added optional properties: {', '.join(added_optional)}")
        severity = "minor"

    for prop in sorted(set(old_properties) & set(new_properties)):
        old_prop = old_properties[prop]
        new_prop = new_properties[prop]
        old_type = old_prop.get("type")
        new_type = new_prop.get("type")
        if old_type != new_type:
            notes.append(f"Type changed for {prop}: {old_type} -> {new_type}")
            severity = "major"
            continue

        old_enum = old_prop.get("enum")
        new_enum = new_prop.get("enum")
        if old_enum is not None and new_enum is not None:
            old_enum_set = set(old_enum)
            new_enum_set = set(new_enum)
            if not old_enum_set.issubset(new_enum_set):
                notes.append(f"Enum narrowed for {prop}")
                severity = "major"
            elif old_enum_set != new_enum_set and severity == "patch":
                notes.append(f"Enum expanded for {prop}")
                severity = "minor"

    if severity == "patch" and not notes:
        notes.append("No structural change detected")

    backward = severity in {"patch", "minor"}
    forward = severity == "patch"

    return CompatibilityResult(
        change_type=severity,
        backward_compatible=backward,
        forward_compatible=forward,
        notes=notes,
    )


def parse_semver(version: str) -> tuple[int, int, int]:
    pieces = version.split(".")
    if len(pieces) != 3:
        raise ValueError(f"Version must be semver MAJOR.MINOR.PATCH, got {version!r}")
    return tuple(int(piece) for piece in pieces)  # type: ignore[return-value]


def required_bump(old_version: str, new_version: str) -> ChangeType:
    old = parse_semver(old_version)
    new = parse_semver(new_version)
    if new <= old:
        raise ValueError(f"Version must increase: {old_version} -> {new_version}")
    if new[0] > old[0]:
        return "major"
    if new[1] > old[1]:
        return "minor"
    return "patch"


def is_bump_sufficient(required: ChangeType, actual: ChangeType) -> bool:
    return SEMVER_ORDER[actual] >= SEMVER_ORDER[required]


def git_merge_base(repo_root: Path) -> str | None:
    for candidate in ("origin/main", "origin/master", "main", "master"):
        proc = subprocess.run(
            ["git", "merge-base", "HEAD", candidate],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    return None


def git_changed_files(repo_root: Path, base_ref: str | None) -> list[str]:
    if not base_ref:
        return []
    proc = subprocess.run(
        ["git", "diff", "--name-only", base_ref, "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def git_show_json(repo_root: Path, ref: str, relative_path: str) -> dict[str, Any] | None:
    proc = subprocess.run(
        ["git", "show", f"{ref}:{relative_path}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return json.loads(proc.stdout)
