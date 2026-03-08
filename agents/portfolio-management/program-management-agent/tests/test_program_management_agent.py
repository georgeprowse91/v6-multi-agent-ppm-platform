from __future__ import annotations

import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[3]
SRC_DIR = TESTS_DIR.parent / "src"
sys.path.extend(
    [
        str(SRC_DIR),
        str(REPO_ROOT),
        str(REPO_ROOT / "packages"),
        str(REPO_ROOT / "agents" / "runtime"),
        str(REPO_ROOT / "integrations" / "services" / "integration"),
    ]
)

from program_management_agent import ProgramManagementAgent


class DummyEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.published.append((topic, payload))


def _make_agent(tmp_path: Path) -> ProgramManagementAgent:
    return ProgramManagementAgent(
        config={
            "event_bus": DummyEventBus(),
            "program_store_path": str(tmp_path / "programs.json"),
            "program_roadmap_store_path": str(tmp_path / "roadmaps.json"),
            "program_dependency_store_path": str(tmp_path / "dependencies.json"),
        }
    )


@pytest.mark.anyio
async def test_create_program_returns_program_id(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    result = await agent.process(
        {
            "action": "create_program",
            "tenant_id": "tenant-1",
            "program": {
                "name": "Digital Transformation",
                "description": "Enterprise-wide digital transformation program",
                "strategic_objectives": ["reduce_costs", "improve_agility"],
                "constituent_projects": ["proj-1", "proj-2"],
                "methodology": "hybrid",
            },
        }
    )
    assert result.get("program_id")
    assert result["name"] == "Digital Transformation"
    assert result["status"] == "Planning"


@pytest.mark.anyio
async def test_get_program_returns_not_found_for_missing(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    result = await agent.process(
        {
            "action": "get_program",
            "tenant_id": "tenant-1",
            "program_id": "PROG-DOES-NOT-EXIST",
        }
    )
    assert result.get("error") or result.get("program_id") is None or not result.get("found", True)


@pytest.mark.anyio
async def test_create_then_get_program(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    create_result = await agent.process(
        {
            "action": "create_program",
            "tenant_id": "tenant-2",
            "program": {
                "name": "Cloud Migration Program",
                "description": "Migrate all services to Azure",
                "strategic_objectives": ["cloud_first"],
                "constituent_projects": ["proj-a"],
                "methodology": "predictive",
            },
        }
    )
    program_id = create_result["program_id"]

    get_result = await agent.process(
        {
            "action": "get_program",
            "tenant_id": "tenant-2",
            "program_id": program_id,
        }
    )
    assert (
        get_result.get("program_id") == program_id
        or get_result.get("name") == "Cloud Migration Program"
    )


@pytest.mark.anyio
async def test_validate_input_rejects_missing_action(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    valid = await agent.validate_input({})
    assert valid is False


@pytest.mark.anyio
async def test_validate_input_rejects_invalid_action(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    valid = await agent.validate_input({"action": "not_a_real_action"})
    assert valid is False


@pytest.mark.anyio
async def test_validate_input_rejects_create_program_missing_fields(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    valid = await agent.validate_input(
        {
            "action": "create_program",
            "program": {"description": "Missing name field"},
        }
    )
    assert valid is False


@pytest.mark.anyio
async def test_validate_input_accepts_valid_create_program(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    valid = await agent.validate_input(
        {
            "action": "create_program",
            "program": {
                "name": "Test Program",
                "description": "A test",
                "strategic_objectives": [],
                "constituent_projects": [],
            },
        }
    )
    assert valid is True


@pytest.mark.anyio
async def test_generate_roadmap_for_created_program(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    create_result = await agent.process(
        {
            "action": "create_program",
            "tenant_id": "tenant-3",
            "program": {
                "name": "Roadmap Test Program",
                "description": "Test roadmap generation",
                "strategic_objectives": ["growth"],
                "constituent_projects": ["proj-x", "proj-y"],
                "methodology": "adaptive",
            },
        }
    )
    program_id = create_result["program_id"]

    roadmap_result = await agent.process(
        {
            "action": "generate_roadmap",
            "tenant_id": "tenant-3",
            "program_id": program_id,
        }
    )
    assert roadmap_result is not None
    assert roadmap_result.get("program_id") == program_id or roadmap_result.get("roadmap_id")


@pytest.mark.anyio
async def test_get_capabilities_returns_expected_items(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    caps = agent.get_capabilities()
    assert "program_definition" in caps
    assert "dependency_tracking" in caps
    assert "program_health_monitoring" in caps
