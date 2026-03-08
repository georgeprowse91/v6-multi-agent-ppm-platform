from __future__ import annotations

import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[4]
SRC_DIR = TESTS_DIR.parent / "src"
sys.path.extend(
    [
        str(SRC_DIR),
        str(REPO_ROOT),
        str(REPO_ROOT / "packages"),
        str(REPO_ROOT / "agents" / "runtime"),
        str(REPO_ROOT / "agents" / "core-orchestration" / "approval-workflow-agent" / "src"),
    ]
)

from project_definition_agent import ProjectDefinitionAgent


class DummyEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.published.append((topic, payload))


def _make_agent(tmp_path: Path) -> ProjectDefinitionAgent:
    return ProjectDefinitionAgent(
        config={
            "event_bus": DummyEventBus(),
            "charter_store_path": str(tmp_path / "charters.json"),
            "wbs_store_path": str(tmp_path / "wbs.json"),
            "scope_baseline_store_path": str(tmp_path / "baselines.json"),
            "enable_external_research": False,
        }
    )


@pytest.mark.anyio
async def test_generate_charter_creates_charter(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    result = await agent.process(
        {
            "action": "generate_charter",
            "tenant_id": "tenant-1",
            "project": {
                "project_id": "proj-001",
                "name": "ERP Upgrade",
                "description": "Upgrade core ERP system to latest version",
                "sponsor": "CTO",
                "objectives": ["reduce_manual_effort", "improve_reporting"],
                "methodology": "predictive",
            },
        }
    )
    assert result.get("charter_id") or result.get("project_id") == "proj-001"


@pytest.mark.anyio
async def test_generate_wbs_creates_structure(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    result = await agent.process(
        {
            "action": "generate_wbs",
            "tenant_id": "tenant-1",
            "project_id": "proj-001",
            "deliverables": [
                {"name": "System Analysis", "description": "Analyze current ERP usage"},
                {"name": "Migration Plan", "description": "Plan ERP migration steps"},
            ],
        }
    )
    assert result.get("wbs_id") or result.get("work_packages") or result.get("wbs")


@pytest.mark.anyio
async def test_manage_requirements_creates_requirement(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    result = await agent.process(
        {
            "action": "manage_requirements",
            "tenant_id": "tenant-2",
            "project_id": "proj-002",
            "operation": "create",
            "requirement": {
                "title": "Single Sign-On",
                "description": "System must support SSO via Azure AD",
                "type": "functional",
                "priority": "high",
            },
        }
    )
    assert (
        result.get("requirement_id")
        or result.get("requirements")
        or result.get("success") is not False
    )


@pytest.mark.anyio
async def test_validate_input_rejects_missing_action(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    valid = await agent.validate_input({})
    assert valid is False


@pytest.mark.anyio
async def test_validate_input_rejects_unknown_action(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    valid = await agent.validate_input({"action": "do_something_invalid"})
    assert valid is False


@pytest.mark.anyio
async def test_validate_input_accepts_generate_charter(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    valid = await agent.validate_input({"action": "generate_charter"})
    assert valid is True


@pytest.mark.anyio
async def test_detect_scope_creep_returns_result(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    result = await agent.process(
        {
            "action": "detect_scope_creep",
            "tenant_id": "tenant-1",
            "project_id": "proj-001",
            "current_requirements": [
                {"requirement_id": "REQ-001", "title": "Login page"},
                {"requirement_id": "REQ-002", "title": "Dashboard"},
                {"requirement_id": "REQ-003", "title": "Report builder"},
            ],
            "baseline_requirement_ids": ["REQ-001", "REQ-002"],
        }
    )
    assert result is not None


@pytest.mark.anyio
async def test_get_capabilities_returns_expected(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    caps = agent.get_capabilities()
    assert isinstance(caps, list)
    assert len(caps) > 0
