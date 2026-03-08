"""Action handlers for classifying changes and assessing impact."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from change_configuration_agent import ChangeConfigurationAgent


async def classify_change(agent: ChangeConfigurationAgent, change_id: str) -> dict[str, Any]:
    """Classify change request using AI."""
    agent.logger.info("Classifying change: %s", change_id)

    change = agent.change_requests.get(change_id)
    if not change:
        raise ValueError(f"Change request not found: {change_id}")

    description = f"{change.get('title', '')} {change.get('description', '')}".strip()
    classification, confidence = agent.text_classifier.predict(description)

    # Update change
    change["type"] = classification
    change["routing"] = await determine_routing(classification)
    change["classification_confidence"] = confidence.get(classification, 0.0)
    await agent.db_service.store("change_requests", change_id, change)

    return {
        "change_id": change_id,
        "type": classification,
        "routing": change["routing"],
        "confidence": change["classification_confidence"],
    }


async def assess_impact(agent: ChangeConfigurationAgent, change_id: str) -> dict[str, Any]:
    """Assess change impact."""
    agent.logger.info("Assessing impact for change: %s", change_id)

    change = agent.change_requests.get(change_id)
    if not change:
        raise ValueError(f"Change request not found: {change_id}")

    # Consult other agents for impact
    schedule_impact = await assess_schedule_impact(agent, change)
    cost_impact = await assess_cost_impact(agent, change)
    resource_impact = await assess_resource_impact(agent, change)
    risk_impact = await assess_risk_impact(agent, change)
    compliance_impact = await assess_compliance_impact(agent, change)

    # Analyze CI dependencies
    dependency_impact = await analyze_dependency_impact(agent, change)

    # Predict change impact using AI
    predicted_impact = await predict_change_impact(agent, change)

    impact_assessment = {
        "schedule_impact": schedule_impact,
        "cost_impact": cost_impact,
        "resource_impact": resource_impact,
        "risk_impact": risk_impact,
        "compliance_impact": compliance_impact,
        "dependency_impact": dependency_impact,
        "predicted_impact": predicted_impact,
        "overall_risk_score": await calculate_overall_risk(
            schedule_impact, cost_impact, risk_impact, compliance_impact
        ),
        "assessed_at": datetime.now(timezone.utc).isoformat(),
    }

    # Update change
    change["impact_assessment"] = impact_assessment
    change["impact_assessment"]["trend_tags"] = await build_change_trend_tags(change)
    impact_assessment["risk_adjusted_recommendation"] = await generate_risk_adjusted_recommendation(
        impact_assessment
    )

    await agent.db_service.store("change_requests", change_id, change)

    return {
        "change_id": change_id,
        "impact_assessment": impact_assessment,
        "recommendation": await generate_impact_recommendation(impact_assessment),
    }


async def predict_impact(
    agent: ChangeConfigurationAgent, change_data: dict[str, Any]
) -> dict[str, Any]:
    """Predict impact for ad-hoc change data."""
    if not agent.impact_model:
        raise RuntimeError("Impact model is not initialized")
    prediction = agent.impact_model.predict(change_data)
    mitigation = await recommend_mitigation(prediction)
    return {
        "prediction": prediction,
        "mitigation": mitigation,
        "model_trained": prediction["model_trained"],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def determine_routing(change_type: str) -> str:
    """Determine approval routing based on change type."""
    routing_map = {
        "emergency": "Emergency CAB",
        "standard": "Auto-Approved",
        "normal": "CAB Review",
    }
    return routing_map.get(change_type, "CAB Review")


async def assess_schedule_impact(
    agent: ChangeConfigurationAgent, change: dict[str, Any]
) -> dict[str, Any]:
    """Assess schedule impact of change."""
    if agent.schedule_agent:
        response = await agent.schedule_agent.process(
            {"action": "assess_schedule_impact", "change": change}
        )
        return response
    return {"impact_days": 0, "critical_path_affected": False}


async def assess_cost_impact(
    agent: ChangeConfigurationAgent, change: dict[str, Any]
) -> dict[str, Any]:
    """Assess cost impact of change."""
    if agent.financial_agent:
        response = await agent.financial_agent.process(
            {"action": "assess_cost_impact", "change": change}
        )
        return response
    return {"cost_variance": 0, "budget_available": True}


async def assess_resource_impact(
    agent: ChangeConfigurationAgent, change: dict[str, Any]
) -> dict[str, Any]:
    """Assess resource impact of change."""
    if agent.resource_agent:
        response = await agent.resource_agent.process(
            {"action": "assess_resource_impact", "change": change}
        )
        return response
    return {"resources_required": [], "availability": True}


async def assess_risk_impact(
    agent: ChangeConfigurationAgent, change: dict[str, Any]
) -> dict[str, Any]:
    """Assess risk impact of change."""
    if agent.risk_agent:
        response = await agent.risk_agent.process(
            {"action": "assess_change_risk", "change": change}
        )
        return response
    return {"new_risks": [], "risk_score_increase": 0}


async def assess_compliance_impact(
    agent: ChangeConfigurationAgent, change: dict[str, Any]
) -> dict[str, Any]:
    """Assess compliance and regulatory impact of change."""
    compliance_scope = change.get("compliance_scope", [])
    regulatory_flags = change.get("regulatory_flags", [])
    risk_score = 0
    if compliance_scope:
        risk_score += min(20, 5 * len(compliance_scope))
    if regulatory_flags:
        risk_score += min(30, 10 * len(regulatory_flags))
    return {
        "compliance_scope": compliance_scope,
        "regulatory_flags": regulatory_flags,
        "compliance_risk_score": risk_score,
        "compliance_review_required": bool(compliance_scope or regulatory_flags),
    }


async def analyze_dependency_impact(
    agent: ChangeConfigurationAgent, change: dict[str, Any]
) -> dict[str, Any]:
    """Analyze CI dependency impact."""
    impacted_cis = change.get("impacted_cis", [])
    if not impacted_cis:
        return {"dependent_cis": [], "cascading_impact": False, "dependency_depth": 0}
    if agent.dependency_graph:
        dependent_cis = agent.dependency_graph.get_impacted(impacted_cis)
        return {
            "dependent_cis": dependent_cis,
            "cascading_impact": len(dependent_cis) > 0,
            "dependency_depth": len(dependent_cis),
        }
    return {"dependent_cis": [], "cascading_impact": False, "dependency_depth": 0}


async def predict_change_impact(
    agent: ChangeConfigurationAgent, change: dict[str, Any]
) -> dict[str, Any]:
    """Predict change impact using ML."""
    impacted_cis = change.get("impacted_cis", [])
    criticality_weights = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    complexity = 0.0
    for ci_id in impacted_cis:
        ci = agent.cmdb.get(ci_id, {})
        criticality = str(ci.get("attributes", {}).get("criticality", "medium")).lower()
        complexity += criticality_weights.get(criticality, 2)
    complexity = max(complexity, 1.0)
    features = {
        "complexity": complexity,
        "historical_failure_rate": change.get("historical_failure_rate", 0.1),
        "affected_services": len(impacted_cis),
        "risk_category": change.get("risk_category", "medium"),
    }
    if not agent.impact_model:
        raise RuntimeError("Impact model not initialized")
    prediction = agent.impact_model.predict(features)
    mitigation = await recommend_mitigation(prediction)
    predicted_duration = max(1, int(prediction["impact_score"] * 2 + len(impacted_cis)))
    return {
        "success_probability": prediction["success_probability"],
        "predicted_duration": predicted_duration,
        "impact_score": prediction["impact_score"],
        "impacted_ci_count": len(impacted_cis),
        "risk_category": prediction["risk_category"],
        "mitigation": mitigation,
        "model_trained": prediction["model_trained"],
    }


async def calculate_overall_risk(
    schedule_impact: dict[str, Any],
    cost_impact: dict[str, Any],
    risk_impact: dict[str, Any],
    compliance_impact: dict[str, Any],
) -> float:
    """Calculate overall risk score for change."""
    score = 0.0

    if schedule_impact.get("critical_path_affected"):
        score += 30

    if cost_impact.get("cost_variance", 0) > 10000:
        score += 20

    score += risk_impact.get("risk_score_increase", 0)
    score += compliance_impact.get("compliance_risk_score", 0)

    return min(100, score)  # type: ignore


async def generate_risk_adjusted_recommendation(
    impact_assessment: dict[str, Any],
) -> dict[str, Any]:
    predicted = impact_assessment.get("predicted_impact", {})
    success_probability = predicted.get("success_probability", 0.5)
    risk_score = impact_assessment.get("overall_risk_score", 0)
    recommendation = await generate_impact_recommendation(impact_assessment)
    if success_probability < 0.6 or risk_score > 70:
        recommendation = "Escalate for executive review and require enhanced testing."
    return {
        "recommendation": recommendation,
        "success_probability": success_probability,
        "risk_score": risk_score,
    }


async def generate_impact_recommendation(impact_assessment: dict[str, Any]) -> str:
    """Generate recommendation based on impact assessment."""
    risk_score = impact_assessment.get("overall_risk_score", 0)

    if risk_score > 70:
        return "High risk change. Recommend detailed review by CAB and additional testing."
    elif risk_score > 40:
        return "Medium risk change. Recommend standard CAB review and testing."
    else:
        return "Low risk change. Can proceed with standard approval process."


async def recommend_mitigation(prediction: dict[str, Any]) -> list[str]:
    """Recommend mitigation steps based on impact prediction."""
    mitigations = ["Schedule change in maintenance window", "Prepare rollback plan"]
    if prediction.get("risk_category") in {"high", "critical"}:
        mitigations.extend(
            [
                "Run enhanced security scanning",
                "Perform additional peer review",
                "Increase monitoring during deployment",
            ]
        )
    return mitigations


async def build_change_trend_tags(change: dict[str, Any]) -> list[str]:
    tags = []
    classification = change.get("classification", {})
    if classification.get("category"):
        tags.append(f"category:{classification['category']}")
    if change.get("priority"):
        tags.append(f"priority:{change['priority']}")
    if change.get("type"):
        tags.append(f"type:{change['type']}")
    return tags
