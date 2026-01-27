import pytest
from demand_intake_agent import DemandIntakeAgent


@pytest.mark.asyncio
async def test_demand_intake_duplicate_detection_and_search(tmp_path):
    agent = DemandIntakeAgent(
        config={
            "similarity_threshold": 0.2,
            "demand_store_path": tmp_path / "demand_store.json",
        }
    )
    await agent.initialize()

    await agent.process(
        {
            "action": "submit_request",
            "request": {
                "title": "Upgrade CRM platform",
                "description": "Implement new CRM system for sales",
                "business_objective": "Improve sales pipeline visibility",
                "requester": "alice",
            },
        }
    )

    response = await agent.process(
        {
            "action": "submit_request",
            "request": {
                "title": "CRM modernization",
                "description": "New CRM implementation for sales team",
                "business_objective": "Increase pipeline visibility",
                "requester": "bob",
            },
        }
    )

    assert response["duplicates_found"] is True
    assert response["similar_requests"]

    pipeline = await agent.process({"action": "get_pipeline", "filters": {"query": "CRM sales"}})
    assert pipeline["total_requests"] == 2
    assert pipeline["items"][0]["title"] in {"Upgrade CRM platform", "CRM modernization"}


@pytest.mark.asyncio
async def test_demand_intake_check_duplicates(tmp_path):
    agent = DemandIntakeAgent(config={"demand_store_path": tmp_path / "demand_store.json"})
    await agent.initialize()

    await agent.process(
        {
            "action": "submit_request",
            "request": {
                "title": "Upgrade data warehouse",
                "description": "New warehouse",
                "business_objective": "Insights",
                "requester": "alice",
            },
        }
    )

    response = await agent.process(
        {
            "action": "check_duplicates",
            "request": {
                "title": "Upgrade data warehouse",
                "description": "Warehouse improvements",
                "business_objective": "Insights",
                "requester": "bob",
            },
        }
    )

    assert "duplicates_found" in response


@pytest.mark.asyncio
async def test_demand_intake_validation_rejects_missing_fields(tmp_path):
    agent = DemandIntakeAgent(config={"demand_store_path": tmp_path / "demand_store.json"})
    await agent.initialize()

    valid = await agent.validate_input({"action": "submit_request", "request": {"title": "X"}})

    assert valid is False


@pytest.mark.asyncio
async def test_demand_intake_validation_rejects_invalid_action(tmp_path):
    agent = DemandIntakeAgent(config={"demand_store_path": tmp_path / "demand_store.json"})
    await agent.initialize()

    response = await agent.process({"action": "get_pipeline", "filters": {}})

    assert "total_requests" in response

    with pytest.raises(ValueError):
        await agent.process({"action": "bad_action"})
