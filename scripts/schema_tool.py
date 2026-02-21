#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

from schema_registry import (
    SchemaRegistry,
    compare_schemas,
    git_changed_files,
    git_merge_base,
    git_show_json,
    is_bump_sufficient,
    parse_semver,
    required_bump,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def cmd_validate(args: argparse.Namespace) -> int:
    registry = SchemaRegistry(REPO_ROOT)
    failures: list[str] = []
    validator_cls = None
    if importlib.util.find_spec("jsonschema") is not None:
        from jsonschema import Draft202012Validator  # type: ignore

        validator_cls = Draft202012Validator

    for record in registry.iter_schemas():
        try:
            if validator_cls is not None:
                validator_cls.check_schema(record.schema)
            parse_semver(record.metadata.version)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{record.path.relative_to(REPO_ROOT)}: {exc}")
    if failures:
        for failure in failures:
            print(f"Schema registry validation failed: {failure}")
        return 1
    print("Schema registry validation succeeded.")
    return 0


def cmd_compatibility(args: argparse.Namespace) -> int:
    path = REPO_ROOT / args.schema_path
    if not path.exists():
        print(f"Schema file not found: {args.schema_path}")
        return 1
    current = json.loads(path.read_text())
    previous = git_show_json(REPO_ROOT, args.base_ref, args.schema_path)
    if previous is None:
        print(f"No baseline schema found at {args.base_ref}:{args.schema_path}")
        return 1

    result = compare_schemas(previous, current)
    compatible = {
        "backward": result.backward_compatible,
        "forward": result.forward_compatible,
        "full": result.backward_compatible and result.forward_compatible,
    }[args.mode]
    print(f"Change type: {result.change_type}")
    for note in result.notes:
        print(f" - {note}")
    if not compatible:
        print(f"Compatibility check failed for mode={args.mode}")
        return 1
    print(f"Compatibility check passed for mode={args.mode}")
    return 0


def cmd_enforce_bumps(args: argparse.Namespace) -> int:
    registry = SchemaRegistry(REPO_ROOT)
    records_by_relative = {
        str(record.path.relative_to(REPO_ROOT)): record
        for record in registry.iter_schemas()
    }
    base = git_merge_base(REPO_ROOT)
    if not base:
        print("Could not determine merge-base; skipping semantic version enforcement.")
        return 0

    changed = [path for path in git_changed_files(REPO_ROOT, base) if path in records_by_relative]
    failures: list[str] = []
    for relative_path in changed:
        record = records_by_relative[relative_path]
        previous_schema = git_show_json(REPO_ROOT, base, relative_path)
        if previous_schema is None:
            continue
        old_meta = previous_schema.get("x-schema-metadata", {})
        old_version = old_meta.get("version", "1.0.0")
        result = compare_schemas(previous_schema, record.schema)

        try:
            actual_bump = required_bump(old_version, record.metadata.version)
        except ValueError as exc:
            failures.append(f"{relative_path}: {exc}")
            continue

        if not is_bump_sufficient(result.change_type, actual_bump):
            failures.append(
                f"{relative_path}: required {result.change_type} bump due to {', '.join(result.notes)}; "
                f"found {old_version} -> {record.metadata.version} ({actual_bump})"
            )

        mode = record.metadata.compatibility_mode
        mode_ok = {
            "backward": result.backward_compatible,
            "forward": result.forward_compatible,
            "full": result.backward_compatible and result.forward_compatible,
        }[mode]
        if not mode_ok:
            failures.append(
                f"{relative_path}: compatibility_mode={mode} violated by change_type={result.change_type}"
            )

    if failures:
        for failure in failures:
            print(f"Semantic version enforcement failed: {failure}")
        return 1

    print("Semantic version enforcement passed.")
    return 0


def _migration_path(schema_name: str, from_version: str, to_version: str) -> Path:
    return REPO_ROOT / "data" / "schemas" / "migrations" / schema_name / f"{from_version}_to_{to_version}.py"


def cmd_migration_scaffold(args: argparse.Namespace) -> int:
    parse_semver(args.from_version)
    parse_semver(args.to_version)
    target = _migration_path(args.schema, args.from_version, args.to_version)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not args.force:
        print(f"Migration already exists: {target.relative_to(REPO_ROOT)}")
        return 1

    template = f'''"""Migration for {args.schema}: {args.from_version} -> {args.to_version}."""
from __future__ import annotations


def transform(document: dict) -> dict:
    """Transform fixture snapshot from {args.from_version} to {args.to_version}.

    Implement the field-level changes needed for this schema version bump.
    Common operations include:
    - Renaming fields: updated["new_name"] = updated.pop("old_name")
    - Adding fields with defaults: updated.setdefault("new_field", default_value)
    - Removing deprecated fields: updated.pop("deprecated_field", None)
    - Converting value types: updated["field"] = str(updated["field"])
    - Restructuring nested objects: updated["nested"] = {{"key": updated.pop("flat_key")}}
    """
    updated = dict(document)
    # Implement field transformations required for version {args.from_version} -> {args.to_version}.
    return updated
'''
    target.write_text(template)
    print(f"Created migration scaffold: {target.relative_to(REPO_ROOT)}")
    return 0


def _load_transform(path: Path):
    namespace: dict[str, object] = {}
    exec(path.read_text(), namespace)  # noqa: S102
    transform = namespace.get("transform")
    if not callable(transform):
        raise ValueError(f"Migration script missing callable transform(): {path}")
    return transform


def cmd_migration_dry_run(args: argparse.Namespace) -> int:
    migration_script = _migration_path(args.schema, args.from_version, args.to_version)
    if not migration_script.exists():
        print(f"Migration script not found: {migration_script.relative_to(REPO_ROOT)}")
        return 1

    fixture = REPO_ROOT / "data" / "schemas" / "examples" / f"{args.schema}.json"
    if not fixture.exists():
        print(f"Fixture snapshot not found: {fixture.relative_to(REPO_ROOT)}")
        return 1

    payload = json.loads(fixture.read_text())
    transform = _load_transform(migration_script)
    transformed = transform(payload)
    print(json.dumps(transformed, indent=2, sort_keys=True))
    print("Migration dry-run completed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Schema registry tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validate schema registry metadata and JSON Schema syntax")
    validate.set_defaults(func=cmd_validate)

    compat = sub.add_parser("compatibility", help="Run compatibility checks for one schema")
    compat.add_argument("schema_path")
    compat.add_argument("--base-ref", required=True)
    compat.add_argument("--mode", choices=["backward", "forward", "full"], default="full")
    compat.set_defaults(func=cmd_compatibility)

    enforce = sub.add_parser("enforce-bumps", help="Enforce semantic version bumps for changed schemas")
    enforce.set_defaults(func=cmd_enforce_bumps)

    migration = sub.add_parser("migration", help="Migration helpers")
    migration_sub = migration.add_subparsers(dest="migration_command", required=True)

    scaffold = migration_sub.add_parser("scaffold", help="Create migration scaffold script")
    scaffold.add_argument("--schema", required=True)
    scaffold.add_argument("--from-version", required=True)
    scaffold.add_argument("--to-version", required=True)
    scaffold.add_argument("--force", action="store_true")
    scaffold.set_defaults(func=cmd_migration_scaffold)

    dry_run = migration_sub.add_parser("dry-run", help="Apply migration to fixture snapshot")
    dry_run.add_argument("--schema", required=True)
    dry_run.add_argument("--from-version", required=True)
    dry_run.add_argument("--to-version", required=True)
    dry_run.set_defaults(func=cmd_migration_dry_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
