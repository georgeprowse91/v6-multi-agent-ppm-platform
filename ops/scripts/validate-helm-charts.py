#!/usr/bin/env python3
"""Lightweight validation for Helm chart scaffolding in the repo."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import yaml

DEFAULT_HELM_DIRS = [
    Path("apps/api-gateway/helm"),
    Path("apps/admin-console/helm"),
    Path("apps/analytics-service/helm"),
    Path("apps/document-service/helm"),
    Path("apps/orchestration-service/helm"),
    Path("apps/web/helm"),
    Path("apps/connector-hub/helm"),
    Path("apps/workflow-service/helm"),
    Path("services/audit-log/helm"),
    Path("services/data-sync-service/helm"),
    Path("services/identity-access/helm"),
    Path("services/notification-service/helm"),
    Path("services/policy-engine/helm"),
    Path("services/telemetry-service/helm"),
]

REQUIRED_FILES = [
    "Chart.yaml",
    "values.yaml",
    "templates/deployment.yaml",
    "templates/service.yaml",
    "templates/configmap.yaml",
    "templates/_helpers.tpl",
]


class HelmValidationError(Exception):
    pass


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise HelmValidationError(f"{path} must contain a YAML mapping")
    return data


def validate_helm_chart(chart_dir: Path) -> None:
    if not chart_dir.exists():
        raise HelmValidationError(f"Chart directory missing: {chart_dir}")
    for file in REQUIRED_FILES:
        if not (chart_dir / file).exists():
            raise HelmValidationError(f"Missing {file} in {chart_dir}")
    chart_yaml = _load_yaml(chart_dir / "Chart.yaml")
    if chart_yaml.get("apiVersion") != "v2":
        raise HelmValidationError(f"Chart apiVersion must be v2 in {chart_dir}")
    expected_name = chart_dir.parent.name
    if chart_yaml.get("name") != expected_name:
        raise HelmValidationError(
            f"Chart name {chart_yaml.get('name')} does not match {expected_name}"
        )


def validate_helm_charts(dirs: Iterable[Path]) -> None:
    for chart_dir in dirs:
        validate_helm_chart(chart_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Helm chart scaffolding.")
    parser.add_argument("paths", nargs="*", type=Path, help="Optional chart directories")
    args = parser.parse_args()
    chart_dirs = list(args.paths or DEFAULT_HELM_DIRS)
    validate_helm_charts(chart_dirs)
    print(f"Validated {len(chart_dirs)} Helm chart(s) successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
