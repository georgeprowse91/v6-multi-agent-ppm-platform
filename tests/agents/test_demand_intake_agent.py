import pytest
from demand_intake_agent import DemandIntakeAgent


@pytest.mark.asyncio
async def test_demand_intake_duplicate_detection_and_search():
    agent = DemandIntakeAgent(config={"similarity_threshold": 0.2})
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
