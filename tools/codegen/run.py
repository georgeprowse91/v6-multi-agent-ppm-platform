"""OpenAPI validation and summary generation for the repo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from tools.runtime_paths import repo_root, safe_join


def _load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"Missing codegen config at {config_path}.")
    return yaml.safe_load(config_path.read_text()) or {}


def _validate_spec(spec: dict[str, Any], spec_path: Path) -> None:
    missing = [key for key in ("openapi", "info", "paths") if key not in spec]
    if missing:
        raise SystemExit(
            f"OpenAPI spec {spec_path} missing required keys: {', '.join(missing)}."
        )


def _summarize_spec(spec: dict[str, Any]) -> dict[str, Any]:
    paths = spec.get("paths", {}) or {}
    operations = 0
    for methods in paths.values():
        if isinstance(methods, dict):
            operations += len([m for m in methods.keys() if m.lower() in {"get", "post", "put", "patch", "delete"}])

    info = spec.get("info", {}) or {}
    return {
        "openapi": spec.get("openapi"),
        "title": info.get("title"),
        "version": info.get("version"),
        "path_count": len(paths),
        "operation_count": operations,
    }


def _write_outputs(
    output_dir: Path,
    summary_filename: str,
    paths_filename: str,
    summary: dict[str, Any],
    paths: list[str],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / summary_filename
    paths_path = output_dir / paths_filename

    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    paths_path.write_text("\n".join(paths) + "\n")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate OpenAPI summaries.")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parent / "codegen_config.yaml"),
        help="Path to the codegen config file.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config = _load_config(Path(args.config))

    root = repo_root()
    spec_path = safe_join(root, config["spec_path"], require_exists=True, should_be_dir=False)
    output_dir = safe_join(root, config["output_dir"], require_exists=False, should_be_dir=True)

    spec = yaml.safe_load(spec_path.read_text())
    if not isinstance(spec, dict):
        raise SystemExit(f"OpenAPI spec {spec_path} is not a mapping.")

    _validate_spec(spec, spec_path)

    summary = _summarize_spec(spec)
    paths = sorted(spec.get("paths", {}).keys())
    _write_outputs(
        output_dir,
        config["summary_filename"],
        config["paths_filename"],
        summary,
        paths,
    )
    print(f"Generated OpenAPI summary at {output_dir}.")


if __name__ == "__main__":
    main()
