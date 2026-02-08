"""Minimal runtime evaluation harness for manifest/fixture checks."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


class EvaluationError(Exception):
    pass


def _resolve_path(payload: Any, path: str) -> Any:
    current = payload
    for segment in path.split("."):
        if "[" in segment and segment.endswith("]"):
            name, index_str = segment[:-1].split("[")
            if name:
                current = current[name]
            current = current[int(index_str)]
        else:
            current = current[segment]
    return current


def _check_assertion(payload: dict[str, Any], assertion: dict[str, Any]) -> list[str]:
    field = assertion.get("field")
    if not field:
        return ["Assertion missing 'field'."]

    try:
        value = _resolve_path(payload, field)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        return [f"Failed to resolve '{field}': {exc}"]

    if "equals" in assertion:
        expected = assertion["equals"]
        if value != expected:
            return [f"Expected {field} == {expected!r}, got {value!r}"]

    if "contains" in assertion:
        expected = assertion["contains"]
        if not isinstance(value, str) or expected not in value:
            return [f"Expected {field} to contain {expected!r}, got {value!r}"]

    return []


def run_manifest(manifest_path: Path) -> int:
    manifest = yaml.safe_load(manifest_path.read_text())
    evaluations = manifest.get("evaluations", [])
    failures: list[str] = []

    for evaluation in evaluations:
        fixture_path = manifest_path.parent / evaluation["fixture"]
        fixture = yaml.safe_load(fixture_path.read_text())
        for assertion in evaluation.get("assertions", []):
            failures.extend(
                f"{evaluation['id']}: {message}"
                for message in _check_assertion(fixture, assertion)
            )

    if failures:
        raise EvaluationError("\n".join(failures))

    return len(evaluations)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).with_name("manifest.yaml"),
        help="Path to the evaluation manifest YAML.",
    )
    args = parser.parse_args()

    try:
        total = run_manifest(args.manifest)
    except EvaluationError as exc:
        raise SystemExit(f"Evaluation failed:\n{exc}") from exc

    print(f"{total} evaluations passed.")


if __name__ == "__main__":
    main()
