from __future__ import annotations

import asyncio

import pytest

from agents.runtime.src.base_agent import BaseAgent
from agents.runtime.src.orchestrator import AgentTask, Orchestrator
from tests.helpers.service_bus import build_test_event_bus


class RiskRecommendationAgent(BaseAgent):
    async def process(self, input_data: dict) -> dict:
        return {
            "proposed_actions": [
                {
                    "action_type": "risk_mitigation",
                    "risk_score": 0.92,
                    "recommendation": "Escalate to steering committee",
                }
            ]
        }


@pytest.mark.asyncio
async def test_high_risk_action_requires_human_review_and_can_be_approved() -> None:
    event_bus = build_test_event_bus()
    orchestrator = Orchestrator(event_bus=event_bus)

    async def on_review_required(payload: dict) -> None:
        await event_bus.publish(
            "human_review_decision",
            {
                "review_id": payload["review_id"],
                "decision": "approve",
                "reviewer": "pmo-analyst",
            },
        )

    event_bus.subscribe("human_review_required", on_review_required)

    result = await orchestrator.run(
        [
            AgentTask(
                task_id="risk-task",
                agent=RiskRecommendationAgent("agent-15-risk-management"),
            )
        ],
        context={"correlation_id": "corr-approve"},
    )

    action = result.results["risk-task"]["data"]["proposed_actions"][0]
    review_metadata = result.results["risk-task"]["metadata"]["human_review"]

    assert action["status"] == "approved_by_human_review"
    assert review_metadata[0]["decision"] == "approve"
    assert orchestrator.get_pending_human_reviews() == []


@pytest.mark.asyncio
async def test_high_risk_action_can_be_rejected_by_human_review() -> None:
    event_bus = build_test_event_bus()
    orchestrator = Orchestrator(event_bus=event_bus)
    queued_review_ids: list[str] = []
    gate = asyncio.Event()

    async def on_review_required(payload: dict) -> None:
        queued_review_ids.append(payload["review_id"])
        gate.set()

    event_bus.subscribe("human_review_required", on_review_required)

    run_task = asyncio.create_task(
        orchestrator.run(
            [
                AgentTask(
                    task_id="risk-task",
                    agent=RiskRecommendationAgent("agent-15-risk-management"),
                )
            ],
            context={"correlation_id": "corr-reject"},
        )
    )

    await asyncio.wait_for(gate.wait(), timeout=2)
    pending = orchestrator.get_pending_human_reviews()
    assert len(pending) == 1
    assert pending[0]["review_id"] == queued_review_ids[0]

    await event_bus.publish(
        "human_review_decision",
        {
            "review_id": queued_review_ids[0],
            "decision": "reject",
            "reviewer": "delivery-lead",
        },
    )

    result = await asyncio.wait_for(run_task, timeout=2)
    action = result.results["risk-task"]["data"]["proposed_actions"][0]
    review_metadata = result.results["risk-task"]["metadata"]["human_review"]

    assert action["status"] == "rejected_by_human_review"
    assert review_metadata[0]["decision"] == "reject"
