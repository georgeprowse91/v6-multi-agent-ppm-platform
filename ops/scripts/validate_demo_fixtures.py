#!/usr/bin/env python3
"""Validate demo fixture coverage and schema for all agent directories."""

from __future__ import annotations

import json
from pathlib import Path

EXPECTED_AGENT_COUNT = 25
ALLOWED_ARTIFACT_TYPES = {
    "document",
    "register",
    "schedule",
    "dashboard",
    "approval",
    "policy",
    "notification",
    "workspace",
}


class DemoFixtureValidationError(Exception):
    """Raised when demo fixture validation fails."""


def discover_agent_directories(repo_root: Path) -> list[Path]:
    agents_root = repo_root / "agents"
    return sorted(path for path in agents_root.glob("**/*-agent") if path.is_dir() and "runtime" not in str(path))


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise DemoFixtureValidationError(message)


def validate_fixture(agent_dir: Path) -> None:
    agent_id = agent_dir.name
    fixture_path = agent_dir / "demo-fixtures" / "sample-response.json"
    _expect(fixture_path.exists(), f"Missing fixture for {agent_id}: {fixture_path}")

    try:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DemoFixtureValidationError(
            f"Invalid JSON in fixture for {agent_id}: {fixture_path} ({exc})"
        ) from exc

    _expect(isinstance(payload, dict), f"Fixture root must be an object: {fixture_path}")
    scripted_response = payload.get("scripted_response")
    _expect(
        isinstance(scripted_response, dict),
        f"Fixture missing scripted_response object: {fixture_path}",
    )
    _expect(
        scripted_response.get("success") is True,
        f"scripted_response.success must be true: {fixture_path}",
    )

    data = scripted_response.get("data")
    _expect(isinstance(data, dict), f"scripted_response.data must be an object: {fixture_path}")
    _expect(data.get("demo") is True, f"data.demo must be true: {fixture_path}")
    _expect(data.get("agent_id") == agent_id, f"data.agent_id must be {agent_id}: {fixture_path}")
    _expect(isinstance(data.get("summary"), str) and data["summary"].strip(), f"data.summary must be a non-empty string: {fixture_path}")

    artifacts = data.get("artifacts")
    _expect(isinstance(artifacts, list) and artifacts, f"data.artifacts must be a non-empty list: {fixture_path}")
    for index, artifact in enumerate(artifacts):
        _expect(isinstance(artifact, dict), f"artifact[{index}] must be an object: {fixture_path}")
        artifact_type = artifact.get("type")
        _expect(
            artifact_type in ALLOWED_ARTIFACT_TYPES,
            f"artifact[{index}].type must be one of {sorted(ALLOWED_ARTIFACT_TYPES)}: {fixture_path}",
        )
        _expect(isinstance(artifact.get("id"), str) and artifact["id"].strip(), f"artifact[{index}].id must be a non-empty string: {fixture_path}")
        _expect(isinstance(artifact.get("title"), str) and artifact["title"].strip(), f"artifact[{index}].title must be a non-empty string: {fixture_path}")


def validate_demo_fixtures(repo_root: Path) -> tuple[int, int]:
    agent_dirs = discover_agent_directories(repo_root)
    _expect(
        len(agent_dirs) == EXPECTED_AGENT_COUNT,
        f"Expected {EXPECTED_AGENT_COUNT} agent directories, found {len(agent_dirs)}",
    )
    for agent_dir in agent_dirs:
        validate_fixture(agent_dir)
    return len(agent_dirs), EXPECTED_AGENT_COUNT


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    present, expected = validate_demo_fixtures(repo_root)
    print(f"fixtures present: {present}/{expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
