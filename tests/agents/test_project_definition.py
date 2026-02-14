import os
import sys
import types

import pytest


prometheus_stub = types.ModuleType("prometheus_client")


class _Metric:
    def __init__(self, *args, **kwargs):
        pass

    def labels(self, *args, **kwargs):
        return self

    def inc(self, *args, **kwargs):
        return None

    def observe(self, *args, **kwargs):
        return None


prometheus_stub.Counter = _Metric
prometheus_stub.Histogram = _Metric
sys.modules["prometheus_client"] = prometheus_stub


runtime_paths_stub = types.ModuleType("tools.runtime_paths")


def _bootstrap_runtime_paths(*_args, **_kwargs):
    return None


runtime_paths_stub.bootstrap_runtime_paths = _bootstrap_runtime_paths
sys.modules["tools.runtime_paths"] = runtime_paths_stub


from pydantic import BaseModel


events_stub = types.ModuleType("events")


class _Event(BaseModel):
    event_name: str
    event_id: str
    timestamp: object
    tenant_id: str
    correlation_id: str
    trace_id: str | None = None
    payload: dict


events_stub.CharterCreatedEvent = _Event
events_stub.WbsCreatedEvent = _Event
events_stub.ScopeChangeEvent = _Event
sys.modules["events"] = events_stub

from project_definition_agent import ProjectDefinitionAgent


class EventCollector:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


@pytest.mark.asyncio
async def test_project_definition_charter_and_wbs_structure_and_events(tmp_path) -> None:
    event_bus = EventCollector()
    os.environ["SCOPE_BASELINE_DB_URL"] = f"sqlite:///{tmp_path / 'scope_baseline.db'}"
    agent = ProjectDefinitionAgent(
        config={
            "event_bus": event_bus,
            "charter_store_path": tmp_path / "charters.json",
            "wbs_store_path": tmp_path / "wbs.json",
        }
    )
    await agent.initialize()

    charter = await agent.process(
        {
            "action": "generate_charter",
            "tenant_id": "tenant-a",
            "charter_data": {
                "title": "Project Helios",
                "description": "Launch customer analytics platform",
                "project_type": "delivery",
                "methodology": "hybrid",
            },
        }
    )

    project_id = charter["project_id"]
    assert charter["charter_id"]
    assert charter["document"].keys() >= {
        "executive_summary",
        "objectives",
        "scope_overview",
        "success_criteria",
    }

    wbs = await agent.process(
        {
            "action": "generate_wbs",
            "tenant_id": "tenant-a",
            "project_id": project_id,
            "scope_statement": {"phase_1": {"name": "Discovery"}},
        }
    )
    assert wbs["wbs_id"]
    assert isinstance(wbs["structure"], dict)
    assert any(topic == "charter.created" for topic, _ in event_bus.events)
    assert any(topic == "wbs.created" for topic, _ in event_bus.events)


@pytest.mark.asyncio
async def test_project_definition_scope_baseline_snapshot(tmp_path) -> None:
    event_bus = EventCollector()
    os.environ["SCOPE_BASELINE_DB_URL"] = f"sqlite:///{tmp_path / 'scope_baseline.db'}"
    agent = ProjectDefinitionAgent(
        config={
            "event_bus": event_bus,
            "charter_store_path": tmp_path / "charters.json",
            "wbs_store_path": tmp_path / "wbs.json",
        }
    )
    await agent.initialize()

    charter = await agent.process(
        {
            "action": "generate_charter",
            "tenant_id": "tenant-a",
            "charter_data": {
                "title": "Project Nova",
                "description": "Improve onboarding",
                "project_type": "delivery",
                "methodology": "adaptive",
            },
        }
    )
    project_id = charter["project_id"]

    await agent.process(
        {
            "action": "generate_wbs",
            "tenant_id": "tenant-a",
            "project_id": project_id,
            "scope_statement": {"phase_1": {"name": "Design"}},
        }
    )
    await agent.process(
        {
            "action": "manage_requirements",
            "project_id": project_id,
            "requirements": [{"text": "System shall support SSO."}],
        }
    )

    baseline = await agent.process({"action": "manage_scope_baseline", "project_id": project_id})
    retrieved = await agent.process(
        {"action": "get_baseline", "baseline_id": baseline["baseline_id"]}
    )

    assert project_id in baseline["baseline_id"]
    assert baseline["status"] == "Locked"
    assert retrieved["baseline_id"] == baseline["baseline_id"]
    assert any(topic == "baseline.created" for topic, _ in event_bus.events)
    assert any(topic == "scope.baseline.locked" for topic, _ in event_bus.events)


@pytest.mark.asyncio
async def test_project_definition_traceability_matrix_covers_all_requirements(tmp_path) -> None:
    os.environ["SCOPE_BASELINE_DB_URL"] = f"sqlite:///{tmp_path / 'scope_baseline.db'}"
    event_bus = EventCollector()
    agent = ProjectDefinitionAgent(
        config={
            "event_bus": event_bus,
            "charter_store_path": tmp_path / "charters.json",
            "wbs_store_path": tmp_path / "wbs.json",
        }
    )
    await agent.initialize()

    charter = await agent.process(
        {
            "action": "generate_charter",
            "tenant_id": "tenant-a",
            "charter_data": {
                "title": "Project Orion",
                "description": "Build shared services",
                "project_type": "delivery",
                "methodology": "hybrid",
            },
        }
    )
    project_id = charter["project_id"]

    await agent.process(
        {
            "action": "generate_wbs",
            "tenant_id": "tenant-a",
            "project_id": project_id,
            "scope_statement": {"phase_1": {"name": "Discovery"}},
        }
    )
    await agent.process(
        {
            "action": "manage_requirements",
            "project_id": project_id,
            "requirements": [
                {"id": "REQ-1", "text": "System shall support SSO."},
                {"id": "REQ-2", "text": "System must emit audit logs."},
            ],
        }
    )

    matrix = await agent.process({"action": "create_traceability_matrix", "project_id": project_id})

    assert len(matrix["traceability_links"]) == 2
    assert matrix["coverage"] == 1.0
    assert all(entry["coverage_status"] == "covered" for entry in matrix["traceability_links"])
    assert any(topic == "traceability.matrix.created" for topic, _ in event_bus.events)
