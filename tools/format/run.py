"""Formatting entrypoint for repo sources."""

from __future__ import annotations

import argparse
import subprocess
from collections.abc import Iterable
from pathlib import Path

import yaml

from tools.runtime_paths import repo_root, safe_join


def _load_config(config_path: Path) -> list[str]:
    if not config_path.exists():
        raise FileNotFoundError(f"Missing format config at {config_path}.")
    config = yaml.safe_load(config_path.read_text()) or {}
    return list(config.get("paths", []))


def _resolve_paths(root: Path, paths: Iterable[str]) -> list[str]:
    resolved = []
    for path in paths:
        resolved.append(str(safe_join(root, path, require_exists=True)))
    return resolved


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Format repo sources with Ruff and Black.")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parent / "format_config.yaml"),
        help="Path to format config file.",
    )
    parser.add_argument("--paths", nargs="*", help="Paths to format (overrides config).")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config_paths = _load_config(Path(args.config))
    target_paths = args.paths or config_paths
    if not target_paths:
        raise SystemExit("No paths configured for formatting.")

    root = repo_root()
    resolved_paths = _resolve_paths(root, target_paths)
    subprocess.run(["python", "-m", "ruff", "check", "--fix", *resolved_paths], check=True)
    subprocess.run(["python", "-m", "black", *resolved_paths], check=True)


if __name__ == "__main__":
    main()
