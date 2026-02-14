import pytest

from agents.runtime.src.event_bus import EventBus
from agents.runtime.src.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_template_workflow_routes_agents_and_requires_review() -> None:
    orchestrator = Orchestrator(event_bus=EventBus())
    result = await orchestrator.run_template_workflow(
        template_id="hybrid-transformation",
        lifecycle_event="publish",
        context_refs={"completed_templates": {"predictive-infrastructure": True}},
    )

    assert result.results
    assert result.context.get("human_review_required") is True
