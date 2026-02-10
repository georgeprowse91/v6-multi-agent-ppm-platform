"""Tests for agent feedback capture and persistence."""

import pytest

from agents.runtime import AgentResponse, BaseAgent
from packages.feedback import Feedback


class FeedbackEnabledAgent(BaseAgent):
    async def process(self, input_data: dict) -> dict:
        return {"message": "ok"}


@pytest.mark.asyncio
async def test_agent_response_can_request_feedback(tmp_path):
    agent = FeedbackEnabledAgent(
        agent_id="feedback-agent",
        config={
            "request_feedback": True,
            "feedback_db_path": str(tmp_path / "feedback.sqlite3"),
        },
    )

    result = await agent.execute({"prompt": "hello"})
    validated = AgentResponse.model_validate(result)

    assert validated.success is True
    assert validated.request_feedback is True


@pytest.mark.asyncio
async def test_send_feedback_persists_record(tmp_path):
    db_path = tmp_path / "feedback.sqlite3"
    agent = FeedbackEnabledAgent(
        agent_id="feedback-agent",
        config={"feedback_db_path": str(db_path)},
    )

    result = await agent.execute({"prompt": "collect this"})
    correlation_id = result["metadata"]["correlation_id"]

    feedback = Feedback(
        correlation_id=correlation_id,
        agent_id="feedback-agent",
        user_rating=4,
        comments="Mostly helpful",
        corrected_response="Use milestone date from source system",
    )

    agent.send_feedback(feedback)
    stored = agent.feedback_service.fetch_by_correlation_id(correlation_id)

    assert len(stored) == 1
    assert stored[0]["agent_id"] == "feedback-agent"
    assert stored[0]["user_rating"] == 4
    assert stored[0]["comments"] == "Mostly helpful"
    assert stored[0]["corrected_response"] == "Use milestone date from source system"
