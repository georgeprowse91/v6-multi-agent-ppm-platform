from datetime import datetime, timedelta

import pytest
from resource_capacity_agent import ResourceCapacityAgent


class EventCollector:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


class FakeMLForecastClient:
    def __init__(self) -> None:
        self.trained_models: list[str] = []
        self.forecast_calls: list[str] = []

    def is_configured(self) -> bool:
        return True

    def train_model(self, model_name, series, horizon, metadata=None):
        self.trained_models.append(model_name)
        return {"model_name": model_name, "trained": True}

    def forecast(self, model_name, series, horizon):
        self.forecast_calls.append(model_name)
        return [0.8 for _ in range(horizon)]


def build_agent_config(tmp_path, **overrides):
    return {
        "event_bus": EventCollector(),
        "resource_store_path": tmp_path / "resources.json",
        "allocation_store_path": tmp_path / "allocations.json",
        "default_tenant_id": "tenant-a",
        **overrides,
    }


@pytest.mark.asyncio
async def test_resource_allocation_persistence_and_events(tmp_path):
    event_bus = EventCollector()
    agent = ResourceCapacityAgent(config=build_agent_config(tmp_path, event_bus=event_bus))
    await agent.initialize()

    add_response = await agent.process(
        {
            "action": "add_resource",
            "tenant_id": "tenant-a",
            "resource": {
                "resource_id": "res-1",
                "name": "Avery",
                "role": "Engineer",
                "skills": ["python"],
                "location": "Remote",
            },
        }
    )
    assert add_response["data_quality"]["is_valid"] is True

    allocation_response = await agent.process(
        {
            "action": "allocate_resource",
            "tenant_id": "tenant-a",
            "correlation_id": "corr-1",
            "allocation": {
                "resource_id": "res-1",
                "project_id": "proj-1",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "allocation_percentage": 50,
            },
        }
    )

    assert allocation_response["allocation_id"]
    assert any(topic == "resource.allocation.created" for topic, _ in event_bus.events)


@pytest.mark.asyncio
async def test_resource_capacity_resource_pool(tmp_path):
    agent = ResourceCapacityAgent(config=build_agent_config(tmp_path))
    await agent.initialize()

    response = await agent.process({"action": "get_resource_pool", "tenant_id": "tenant-a"})

    assert "resources" in response


@pytest.mark.asyncio
async def test_resource_capacity_validation_rejects_invalid_action(tmp_path):
    agent = ResourceCapacityAgent(config=build_agent_config(tmp_path))
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_resource_capacity_validation_rejects_missing_fields(tmp_path):
    agent = ResourceCapacityAgent(config=build_agent_config(tmp_path))
    await agent.initialize()

    valid = await agent.validate_input(
        {"action": "add_resource", "resource": {"resource_id": "res-1"}}
    )

    assert valid is False


@pytest.mark.asyncio
async def test_resource_capacity_skill_matching(tmp_path):
    agent = ResourceCapacityAgent(config=build_agent_config(tmp_path, skill_matching_threshold=0.0))
    await agent.initialize()

    await agent.process(
        {
            "action": "add_resource",
            "tenant_id": "tenant-a",
            "resource": {
                "resource_id": "res-1",
                "name": "Avery",
                "role": "Engineer",
                "skills": ["python", "ml"],
                "location": "Remote",
            },
        }
    )
    await agent.process(
        {
            "action": "add_resource",
            "tenant_id": "tenant-a",
            "resource": {
                "resource_id": "res-2",
                "name": "Jordan",
                "role": "Engineer",
                "skills": ["java"],
                "location": "Remote",
            },
        }
    )

    response = await agent.process(
        {"action": "match_skills", "skills_required": ["python"], "project_context": {}}
    )

    assert response["candidates"][0]["resource_id"] == "res-1"


@pytest.mark.asyncio
async def test_resource_capacity_hr_sync_publishes_events(tmp_path):
    events = EventCollector()
    profiles = [
        {
            "employee_id": "hr-1",
            "name": "Riley",
            "role": "Analyst",
            "skills": ["sql"],
            "status": "Active",
            "source_system": "workday",
        }
    ]
    agent = ResourceCapacityAgent(
        config=build_agent_config(
            tmp_path,
            event_bus=events,
            hr_profiles=profiles,
        )
    )
    await agent.initialize()

    assert any(topic == "resource.added" for topic, _ in events.events)

    profiles[0]["status"] = "Inactive"
    await agent._sync_hr_systems()

    assert any(topic == "resource.updated" for topic, _ in events.events)


@pytest.mark.asyncio
async def test_resource_capacity_training_influences_matching(tmp_path):
    training_records = [
        {
            "resource_id": "res-train",
            "skills": ["kubernetes"],
            "completed": ["kubernetes-fundamentals"],
            "weekly_hours": 4,
        }
    ]
    agent = ResourceCapacityAgent(
        config=build_agent_config(
            tmp_path,
            training_records=training_records,
            skill_matching_threshold=0.0,
        )
    )
    await agent.initialize()

    await agent.process(
        {
            "action": "add_resource",
            "tenant_id": "tenant-a",
            "resource": {
                "resource_id": "res-train",
                "name": "Kai",
                "role": "Engineer",
                "skills": [],
                "location": "Remote",
            },
        }
    )
    await agent._sync_training_records()

    response = await agent.process(
        {"action": "match_skills", "skills_required": ["kubernetes"], "project_context": {}}
    )

    assert response["candidates"][0]["resource_id"] == "res-train"


@pytest.mark.asyncio
async def test_resource_capacity_approval_routing(tmp_path):
    class FakeApprovalClient:
        async def request_approval(self, request, *, tenant_id, correlation_id, approver_hint=None):
            return {"approval_id": "approval-1", "status": "pending", "approvers": [approver_hint]}

        async def record_decision(
            self, approval_id, *, decision, approver_id, comments, tenant_id, correlation_id
        ):
            return {"status": decision}

    approval_client = FakeApprovalClient()
    agent = ResourceCapacityAgent(
        config=build_agent_config(
            tmp_path,
            approval_client=approval_client,
            approval_routing={"default_approver": "resource_lead"},
        )
    )
    await agent.initialize()

    response = await agent.process(
        {
            "action": "request_resource",
            "tenant_id": "tenant-a",
            "request": {
                "project_id": "proj-1",
                "required_skills": ["python"],
                "start_date": "2024-03-01",
                "end_date": "2024-04-01",
                "requested_by": "user-1",
            },
        }
    )

    assert response["approval"]["approval_id"] == "approval-1"
    assert response["approver"] == "resource_lead"


@pytest.mark.asyncio
async def test_resource_capacity_approval_routing_project_role(tmp_path):
    class FakeApprovalClient:
        async def request_approval(self, request, *, tenant_id, correlation_id, approver_hint=None):
            return {"approval_id": "approval-2", "status": "pending", "approvers": [approver_hint]}

        async def record_decision(
            self, approval_id, *, decision, approver_id, comments, tenant_id, correlation_id
        ):
            return {"status": decision}

    approval_client = FakeApprovalClient()
    agent = ResourceCapacityAgent(
        config=build_agent_config(
            tmp_path,
            approval_client=approval_client,
            approval_routing={"by_project_role": {"architect": "chief_architect"}},
        )
    )
    await agent.initialize()

    response = await agent.process(
        {
            "action": "request_resource",
            "tenant_id": "tenant-a",
            "request": {
                "project_id": "proj-2",
                "project_role": "architect",
                "required_skills": ["design"],
                "start_date": "2024-05-01",
                "end_date": "2024-06-01",
                "requested_by": "user-2",
            },
        }
    )

    assert response["approver"] == "chief_architect"


@pytest.mark.asyncio
async def test_resource_capacity_forecasting(tmp_path):
    agent = ResourceCapacityAgent(config=build_agent_config(tmp_path, forecast_horizon_months=3))
    await agent.initialize()

    await agent.process(
        {
            "action": "add_resource",
            "tenant_id": "tenant-a",
            "resource": {
                "resource_id": "res-forecast",
                "name": "Taylor",
                "role": "Analyst",
                "skills": ["planning"],
                "location": "Remote",
            },
        }
    )

    now = datetime.utcnow()
    agent.allocations["res-forecast"] = [
        {
            "allocation_id": "alloc-1",
            "resource_id": "res-forecast",
            "project_id": "proj-1",
            "start_date": (now - timedelta(days=45)).date().isoformat(),
            "end_date": (now - timedelta(days=15)).date().isoformat(),
            "allocation_percentage": 50,
            "status": "Active",
        }
    ]

    forecast = await agent.process(
        {"action": "forecast_capacity", "filters": {"history_months": 3}}
    )

    assert len(forecast["future_capacity"]) == 3
    assert len(forecast["future_demand"]) == 3
    assert "assumptions" in forecast


@pytest.mark.asyncio
async def test_resource_capacity_forecasting_with_ml_client(tmp_path):
    ml_client = FakeMLForecastClient()
    agent = ResourceCapacityAgent(
        config=build_agent_config(tmp_path, forecast_horizon_months=2, ml_forecast_client=ml_client)
    )
    await agent.initialize()

    await agent.process(
        {
            "action": "add_resource",
            "tenant_id": "tenant-a",
            "resource": {
                "resource_id": "res-ml",
                "name": "Morgan",
                "role": "Analyst",
                "skills": ["planning"],
                "location": "Remote",
            },
        }
    )

    forecast = await agent.process(
        {"action": "forecast_capacity", "filters": {"history_months": 2}}
    )

    assert "assumptions" in forecast
    assert forecast["assumptions"]["ml_metadata"]["capacity_model"]["trained"] is True
    assert "tenant-a-capacity" in ml_client.trained_models


@pytest.mark.asyncio
async def test_resource_capacity_conflict_detection(tmp_path):
    agent = ResourceCapacityAgent(config=build_agent_config(tmp_path))
    await agent.initialize()

    await agent.process(
        {
            "action": "add_resource",
            "tenant_id": "tenant-a",
            "resource": {
                "resource_id": "res-conflict",
                "name": "Alex",
                "role": "Engineer",
                "skills": ["python"],
                "location": "Remote",
            },
        }
    )

    agent.allocations["res-conflict"] = [
        {
            "allocation_id": "alloc-a",
            "resource_id": "res-conflict",
            "project_id": "proj-1",
            "start_date": "2024-01-01",
            "end_date": "2024-02-01",
            "allocation_percentage": 60,
            "status": "Active",
        },
        {
            "allocation_id": "alloc-b",
            "resource_id": "res-conflict",
            "project_id": "proj-2",
            "start_date": "2024-01-15",
            "end_date": "2024-02-15",
            "allocation_percentage": 60,
            "status": "Active",
        },
    ]

    conflicts = await agent.process({"action": "identify_conflicts", "filters": {}})

    assert conflicts["total_conflicts"] == 1


@pytest.mark.asyncio
async def test_resource_capacity_enforces_allocation_constraints(tmp_path):
    agent = ResourceCapacityAgent(
        config=build_agent_config(
            tmp_path,
            max_concurrent_allocations=1,
            enforce_allocation_constraints=True,
        )
    )
    await agent.initialize()

    await agent.process(
        {
            "action": "add_resource",
            "tenant_id": "tenant-a",
            "resource": {
                "resource_id": "res-constraint",
                "name": "Jamie",
                "role": "Engineer",
                "skills": ["python"],
                "location": "Remote",
            },
        }
    )

    agent.allocations["res-constraint"] = [
        {
            "allocation_id": "alloc-1",
            "resource_id": "res-constraint",
            "project_id": "proj-1",
            "start_date": "2024-01-01",
            "end_date": "2024-02-01",
            "allocation_percentage": 50,
            "status": "Active",
        }
    ]

    with pytest.raises(ValueError, match="Allocation exceeds maximum concurrent allocation"):
        await agent.process(
            {
                "action": "allocate_resource",
                "tenant_id": "tenant-a",
                "allocation": {
                    "resource_id": "res-constraint",
                    "project_id": "proj-2",
                    "start_date": "2024-01-15",
                    "end_date": "2024-02-15",
                    "allocation_percentage": 25,
                },
            }
        )


@pytest.mark.asyncio
async def test_resource_capacity_performance_scoring(tmp_path):
    agent = ResourceCapacityAgent(config=build_agent_config(tmp_path))
    await agent.initialize()

    await agent.db_service.store(
        "project_performance",
        "perf-1",
        {
            "resource_id": "res-perf",
            "on_time_rate": 0.9,
            "quality_score": 0.95,
            "completion_rate": 0.92,
            "customer_satisfaction": 0.88,
        },
    )

    score = await agent._get_performance_score("res-perf", {})

    assert score >= 0.88


@pytest.mark.asyncio
async def test_resource_capacity_update_and_delete(tmp_path):
    agent = ResourceCapacityAgent(config=build_agent_config(tmp_path))
    await agent.initialize()

    await agent.process(
        {
            "action": "add_resource",
            "tenant_id": "tenant-a",
            "resource": {
                "resource_id": "res-update",
                "name": "River",
                "role": "Engineer",
                "skills": ["python"],
                "location": "Remote",
            },
        }
    )

    update_response = await agent.process(
        {
            "action": "update_resource",
            "tenant_id": "tenant-a",
            "resource": {"resource_id": "res-update", "role": "Lead Engineer"},
        }
    )

    assert update_response["profile"]["role"] == "Lead Engineer"

    delete_response = await agent.process(
        {"action": "delete_resource", "tenant_id": "tenant-a", "resource_id": "res-update"}
    )

    assert delete_response["status"] == "Inactive"
