"""Lint entrypoint for repo sources."""

from __future__ import annotations

import argparse
import subprocess
from collections.abc import Iterable
from pathlib import Path

import yaml

from tools.runtime_paths import repo_root, safe_join


def _load_config(config_path: Path) -> dict[str, list[str]]:
    if not config_path.exists():
        raise FileNotFoundError(f"Missing lint config at {config_path}.")
    return yaml.safe_load(config_path.read_text()) or {}


def _resolve_paths(root: Path, paths: Iterable[str]) -> list[str]:
    resolved = []
    for path in paths:
        resolved.append(str(safe_join(root, path, require_exists=True)))
    return resolved


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run repo lint checks.")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parent / "lint_config.yaml"),
        help="Path to lint config file.",
    )
    parser.add_argument("--paths", nargs="*", help="Paths to lint (overrides config).")
    parser.add_argument("--skip-mypy", action="store_true", help="Skip mypy checks.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config = _load_config(Path(args.config))
    root = repo_root()

    lint_paths = args.paths or config.get("paths", [])
    if not lint_paths:
        raise SystemExit("No paths configured for linting.")
    resolved_paths = _resolve_paths(root, lint_paths)

    subprocess.run(["python", "-m", "ruff", "check", *resolved_paths], check=True)
    subprocess.run(["python", "-m", "black", "--check", *resolved_paths], check=True)

    if not args.skip_mypy:
        mypy_paths = config.get("mypy_paths", lint_paths)
        resolved_mypy_paths = _resolve_paths(root, mypy_paths)
        # Exclude root-level stub files and per-service duplicate modules
        mypy_exclude = (
            r"^(email_validator|events|prompt_registry|pydantic_settings|requests|runtime_flags)\.py$"
            r"|^(sqlalchemy|numpy|integrations|celery|yaml|jwt)(/|$)"
            r"|.*/tests/.*"
            r"|(apps|services|agents)/.*/src/(config|storage|persistence|models|auth|metrics"
            r"|circuit_breaker|leader_election|retention_scheduler|orchestrator|dependencies"
            r"|connectors|analytics|documents|health|lineage|prompts|scope_research|assistant"
            r"|audit|workflow|workspace|web_search|router|main)\.py"
            r"|services/agent-config/src/__init__\.py"
            r"|packages/.*/src/__init__\.py"
        )
        subprocess.run(
            [
                "python",
                "-m",
                "mypy",
                "--explicit-package-bases",
                "--namespace-packages",
                "--exclude",
                mypy_exclude,
                *resolved_mypy_paths,
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
