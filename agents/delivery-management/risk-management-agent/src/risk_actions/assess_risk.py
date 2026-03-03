"""Action handler for risk assessment."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from risk_utils import (
    calculate_quantitative_impact,
    classify_risk_level,
    ensure_local_risk_models,
    predict_risk_metrics,
    publish_risk_event,
    store_risk_dataset,
)

if TYPE_CHECKING:
    from risk_management_agent import RiskManagementAgent


async def assess_risk(agent: RiskManagementAgent, risk_id: str) -> dict[str, Any]:
    """
    Perform detailed risk assessment.

    Returns risk score and classification.
    """
    agent.logger.info("Assessing risk: %s", risk_id)

    risk = agent.risk_register.get(risk_id)
    if not risk:
        raise ValueError(f"Risk not found: {risk_id}")

    # Use predictive models for probability and impact
    await ensure_local_risk_models(agent)
    predicted_assessment = await predict_risk_metrics(agent, risk)

    # Calculate quantitative impact
    quantitative_impact = await calculate_quantitative_impact(agent, risk)

    # Update risk with detailed assessment
    risk["probability"] = predicted_assessment.get("probability", risk["probability"])
    risk["impact"] = predicted_assessment.get("impact", risk["impact"])
    risk["score"] = risk["probability"] * risk["impact"]
    risk["quantitative_impact"] = quantitative_impact
    risk["last_assessed"] = datetime.now(timezone.utc).isoformat()

    if agent.db_service:
        await agent.db_service.store("risks", risk_id, risk)
        await agent.db_service.store(
            "risk_assessments",
            f"{risk_id}-{risk['last_assessed'].replace(':', '-')}",
            {
                "risk_id": risk_id,
                "assessment": predicted_assessment,
                "score": risk["score"],
                "assessed_at": risk["last_assessed"],
            },
        )
        await agent.db_service.store(
            "risk_impacts",
            f"{risk_id}-{risk['last_assessed'].replace(':', '-')}",
            {
                "risk_id": risk_id,
                "quantitative_impact": quantitative_impact,
                "assessed_at": risk["last_assessed"],
            },
        )
    await store_risk_dataset(agent, "risks", [risk], domain="risk_register")
    await publish_risk_event(
        agent,
        "risk.assessed",
        {
            "risk_id": risk_id,
            "score": risk["score"],
            "probability": risk["probability"],
            "impact": risk["impact"],
        },
    )

    return {
        "risk_id": risk_id,
        "title": risk["title"],
        "probability": risk["probability"],
        "impact": risk["impact"],
        "score": risk["score"],
        "risk_level": await classify_risk_level(agent, risk["score"]),
        "quantitative_impact": quantitative_impact,
        "assessment_date": risk["last_assessed"],
    }
