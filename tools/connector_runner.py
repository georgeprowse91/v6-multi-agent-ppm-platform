"""Connector runner for local validation and metadata checks."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

from tools.component_runner import Component, discover_connectors
from tools.runtime_paths import repo_root


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Connector runner for local development.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-connectors", help="List available connectors.")
    list_parser.add_argument("--json", action="store_true", help="Output JSON.")

    run_parser = subparsers.add_parser("run-connector", help="Run a connector.")
    run_parser.add_argument("--name", required=True, help="Connector directory name.")
    run_parser.add_argument("--dry-run", action="store_true", help="Validate without running.")
    run_parser.add_argument("--docker", action="store_true", help="Run via Dockerfile.")

    return parser.parse_args()


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def _validate_connector(connector: Component) -> list[str]:
    issues: list[str] = []
    manifest_path = connector.path / "manifest.yaml"
    manifest = _load_manifest(manifest_path)
    if not manifest:
        issues.append(f"Missing manifest.yaml in {connector.path}.")
        return issues

    if not manifest.get("id"):
        issues.append("manifest.yaml missing required field: id")
    if not manifest.get("version"):
        issues.append("manifest.yaml missing required field: version")

    mappings_dir = connector.path / "mappings"
    if not mappings_dir.exists():
        issues.append("Missing mappings/ directory for connector mappings.")
    return issues


def _execute(command: list[str], cwd: Path, dry_run: bool) -> None:
    display = " ".join(command)
    if dry_run:
        print(f"[dry-run] {display}")
        return
    subprocess.run(command, check=True, cwd=cwd)


def _run_connector(connector: Component, use_docker: bool, dry_run: bool) -> None:
    issues = _validate_connector(connector)
    if issues:
        if dry_run:
            print("Validation issues:")
            for issue in issues:
                print(f"- {issue}")
            return
        raise SystemExit("Connector validation failed:\n" + "\n".join(f"- {i}" for i in issues))

    if dry_run:
        print(f"Connector {connector.name} validated successfully.")
        return

    if use_docker:
        dockerfile = connector.path / "Dockerfile"
        if not dockerfile.exists():
            raise SystemExit(f"No Dockerfile found for {connector.name} at {dockerfile}.")
        image_tag = f"ppm-connector-{connector.name}"
        _execute(
            ["docker", "build", "-t", image_tag, "-f", str(dockerfile), str(connector.path)],
            repo_root(),
            dry_run,
        )
        _execute(["docker", "run", "--rm", image_tag], repo_root(), dry_run)
        return

    raise SystemExit(
        "Connector execution is not yet defined. "
        f"Add a Dockerfile or implement a Python entrypoint under {connector.path}/src."
    )


def _select_connector(name: str) -> Component:
    for connector in discover_connectors():
        if connector.name == name:
            return connector
    available = ", ".join(sorted(c.name for c in discover_connectors()))
    raise SystemExit(f"Connector '{name}' not found. Available: {available or 'none'}.")


def _render_connectors(connectors: list[Component], as_json: bool) -> None:
    if as_json:
        payload = [
            {"name": connector.name, "path": str(connector.path)} for connector in connectors
        ]
        print(json.dumps(payload, indent=2))
        return

    for connector in connectors:
        print(f"{connector.name} -> {connector.path}")


def main() -> None:
    args = _parse_args()
    if args.command == "list-connectors":
        _render_connectors(discover_connectors(), args.json)
        return

    connector = _select_connector(args.name)
    _run_connector(connector, args.docker, args.dry_run)


if __name__ == "__main__":
    main()
