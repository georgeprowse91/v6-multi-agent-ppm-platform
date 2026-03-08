"""Action handler for predictive analytics."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from analytics_utils import generate_prediction_id, get_health_history

if TYPE_CHECKING:
    from analytics_insights_agent import AnalyticsInsightsAgent

# Health score thresholds for alert generation
HEALTH_CRITICAL_THRESHOLD = 0.40
HEALTH_WARNING_THRESHOLD = 0.60
HEALTH_RAPID_DECLINE_DELTA = 0.15

# Signal weights matching HealthPredictor in predictive.py
SIGNAL_WEIGHTS = {"risk": 0.3, "schedule": 0.25, "budget": 0.25, "resource": 0.2}


async def handle_run_prediction(
    agent: AnalyticsInsightsAgent, tenant_id: str, model_type: str, input_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Run predictive analytics model.

    Returns predictions with confidence intervals.
    """
    agent.logger.info("Running prediction: %s", model_type)

    input_data = {**input_data, "tenant_id": tenant_id}

    # Load ML model
    model = await agent.ml_manager.load_model(model_type)

    # Prepare input features
    features = await _prepare_features(input_data, model_type)

    # Make prediction
    prediction = await _make_prediction(agent, model, features, model_type, input_data)

    # Calculate confidence interval
    confidence_interval = await _calculate_confidence_interval(prediction, model_type)

    # Store prediction
    prediction_id = await generate_prediction_id()
    prediction_record = {
        "prediction_id": prediction_id,
        "model_type": model_type,
        "input_data": input_data,
        "prediction": prediction,
        "confidence_interval": confidence_interval,
        "confidence": prediction.get("confidence", 0.0),
        "predicted_at": datetime.now(timezone.utc).isoformat(),
    }
    agent.predictions[prediction_id] = prediction_record
    agent.analytics_output_store.upsert(tenant_id, prediction_id, prediction_record.copy())

    # For health_score predictions, check thresholds and generate alerts
    alerts: list[dict[str, Any]] = []
    if model_type == "health_score":
        alerts = await _check_health_thresholds(agent, tenant_id, input_data, prediction)

    result = {
        "prediction_id": prediction_id,
        "model_type": model_type,
        "prediction": prediction.get("value"),
        "confidence": prediction.get("confidence"),
        "confidence_interval": confidence_interval,
        "recommendations": await _generate_prediction_recommendations(prediction, model_type),
    }
    if alerts:
        result["alerts"] = alerts

    return result


async def _prepare_features(input_data: dict[str, Any], model_type: str) -> list[float]:
    """Prepare features for ML model."""
    if model_type == "health_score":
        return _prepare_health_features(input_data)

    features: list[float] = []
    for value in input_data.values():
        if isinstance(value, (int, float)):
            features.append(float(value))
    return features


def _prepare_health_features(input_data: dict[str, Any]) -> list[float]:
    """Extract signal-specific features for health prediction."""
    signals = input_data.get("signals", {})
    return [
        float(signals.get("risk", 0.5)),
        float(signals.get("schedule", 0.5)),
        float(signals.get("budget", 0.5)),
        float(signals.get("resource", 0.5)),
    ]


def _compute_weighted_health(signals: dict[str, float]) -> float:
    """Compute composite health score from weighted signals."""
    risk = signals.get("risk", 0.5)
    schedule = signals.get("schedule", 0.5)
    budget = signals.get("budget", 0.5)
    resource = signals.get("resource", 0.5)

    return (
        SIGNAL_WEIGHTS["risk"] * (1 - risk)
        + SIGNAL_WEIGHTS["schedule"] * schedule
        + SIGNAL_WEIGHTS["budget"] * budget
        + SIGNAL_WEIGHTS["resource"] * resource
    )


def _compute_trend_slope(history: list[dict[str, Any]]) -> float:
    """Compute linear trend slope from health history using least squares."""
    n = len(history)
    if n < 2:
        return 0.0

    scores = [entry.get("composite_score", 0.5) for entry in history]
    x_mean = (n - 1) / 2.0
    y_mean = sum(scores) / n
    numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(scores))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _compute_volatility(history: list[dict[str, Any]]) -> float:
    """Compute score volatility as standard deviation of changes."""
    if len(history) < 3:
        return 0.0
    scores = [entry.get("composite_score", 0.5) for entry in history]
    deltas = [scores[i] - scores[i - 1] for i in range(1, len(scores))]
    mean_delta = sum(deltas) / len(deltas)
    variance = sum((d - mean_delta) ** 2 for d in deltas) / len(deltas)
    return math.sqrt(variance)


async def _make_prediction(
    agent: AnalyticsInsightsAgent,
    model: dict[str, Any],
    features: list[float],
    model_type: str,
    input_data: dict[str, Any],
) -> dict[str, Any]:
    """Make prediction using ML model or built-in algorithms."""
    if hasattr(model, "predict"):
        predicted_value = model.predict([features])[0]
        return {"value": float(predicted_value), "confidence": 0.8}

    if model_type == "health_score":
        return await _predict_health_score(agent, input_data)

    return {"value": 0.0, "confidence": 0.85}


async def _predict_health_score(
    agent: AnalyticsInsightsAgent, input_data: dict[str, Any]
) -> dict[str, Any]:
    """Multi-signal health score prediction with trend analysis."""
    project_id = input_data.get("project_id")
    tenant_id = input_data.get("tenant_id", "default")
    signals = input_data.get("signals", {})

    history = await get_health_history(agent, tenant_id, project_id)

    # If signals provided directly, compute weighted health
    if signals:
        current_score = _compute_weighted_health(signals)
    elif history:
        current_score = history[-1].get("composite_score", 0.5)
    else:
        current_score = 0.5

    # Compute trend from history
    trend_slope = _compute_trend_slope(history)
    volatility = _compute_volatility(history)

    # Determine decay factor based on trend and volatility
    decay_30d = trend_slope * -1  # negative slope means declining
    if volatility > 0.05:
        decay_30d += volatility * 0.3  # high volatility adds uncertainty

    # Predict future scores with exponential decay
    pred_30 = max(0.0, min(1.0, current_score - decay_30d))
    pred_60 = max(0.0, min(1.0, current_score - decay_30d * 1.8))
    pred_90 = max(0.0, min(1.0, current_score - decay_30d * 2.5))

    # Determine trend direction
    if trend_slope > 0.02:
        trend = "improving"
    elif trend_slope < -0.05:
        trend = "rapidly_declining"
    elif trend_slope < -0.01:
        trend = "declining"
    else:
        trend = "stable"

    # Confidence based on history length and volatility
    base_confidence = min(0.95, 0.5 + len(history) * 0.05)
    confidence = max(0.3, base_confidence - volatility * 2)

    # Build signal breakdown
    breakdown = _build_signal_breakdown(signals, history)

    # Identify risk factors
    risk_factors = _identify_risk_factors(signals, trend_slope, current_score)

    return {
        "value": round(current_score, 4),
        "confidence": round(confidence, 3),
        "predicted_30d": round(pred_30, 4),
        "predicted_60d": round(pred_60, 4),
        "predicted_90d": round(pred_90, 4),
        "trend": trend,
        "trend_slope": round(trend_slope, 4),
        "volatility": round(volatility, 4),
        "breakdown": breakdown,
        "risk_factors": risk_factors,
        "at_risk": current_score < HEALTH_WARNING_THRESHOLD
        or trend in ("declining", "rapidly_declining"),
    }


def _build_signal_breakdown(
    signals: dict[str, float], history: list[dict[str, Any]]
) -> dict[str, Any]:
    """Build per-signal score breakdown."""
    if signals:
        risk = signals.get("risk", 0.5)
        schedule = signals.get("schedule", 0.5)
        budget = signals.get("budget", 0.5)
        resource = signals.get("resource", 0.5)
    elif history:
        latest = history[-1]
        metrics = latest.get("metrics", {})
        risk = (
            metrics.get("risk", {}).get("score", 0.5)
            if isinstance(metrics.get("risk"), dict)
            else 0.5
        )
        schedule = (
            metrics.get("schedule", {}).get("score", 0.5)
            if isinstance(metrics.get("schedule"), dict)
            else 0.5
        )
        budget = (
            metrics.get("budget", {}).get("score", 0.5)
            if isinstance(metrics.get("budget"), dict)
            else 0.5
        )
        resource = (
            metrics.get("resource", {}).get("score", 0.5)
            if isinstance(metrics.get("resource"), dict)
            else 0.5
        )
    else:
        risk = schedule = budget = resource = 0.5

    contributing = []
    if risk > 0.6:
        contributing.append("High risk exposure")
    if schedule < 0.5:
        contributing.append("Schedule slippage")
    if budget < 0.5:
        contributing.append("Budget overrun")
    if resource < 0.5:
        contributing.append("Resource constraints")

    return {
        "risk_score": round(risk, 3),
        "schedule_score": round(schedule, 3),
        "budget_score": round(budget, 3),
        "resource_score": round(resource, 3),
        "contributing_factors": contributing,
    }


def _identify_risk_factors(
    signals: dict[str, float], trend_slope: float, current_score: float
) -> list[str]:
    """Identify contributing risk factors for the health prediction."""
    factors: list[str] = []
    if current_score < HEALTH_CRITICAL_THRESHOLD:
        factors.append("Health score in critical range")
    elif current_score < HEALTH_WARNING_THRESHOLD:
        factors.append("Health score below warning threshold")

    if trend_slope < -0.05:
        factors.append("Rapid downward trend detected")
    elif trend_slope < -0.01:
        factors.append("Gradual declining trend")

    risk = signals.get("risk", 0.5)
    schedule = signals.get("schedule", 0.5)
    budget = signals.get("budget", 0.5)
    resource = signals.get("resource", 0.5)

    if risk > 0.7:
        factors.append("Risk signal elevated above 70%")
    if schedule < 0.4:
        factors.append("Schedule health critically low")
    if budget < 0.4:
        factors.append("Budget health critically low")
    if resource < 0.4:
        factors.append("Resource utilization critically low")

    return factors


async def _check_health_thresholds(
    agent: AnalyticsInsightsAgent,
    tenant_id: str,
    input_data: dict[str, Any],
    prediction: dict[str, Any],
) -> list[dict[str, Any]]:
    """Check health prediction against thresholds and generate alerts."""
    alerts: list[dict[str, Any]] = []
    project_id = input_data.get("project_id", "unknown")
    project_name = input_data.get("project_name", project_id)
    current_score = prediction.get("value", 1.0)
    history = await get_health_history(agent, tenant_id, project_id)

    previous_score = history[-1].get("composite_score", 1.0) if history else 1.0

    now = datetime.now(timezone.utc).isoformat()

    # Check critical threshold crossing
    if current_score < HEALTH_CRITICAL_THRESHOLD and previous_score >= HEALTH_CRITICAL_THRESHOLD:
        alert = {
            "alert_id": await generate_prediction_id(),
            "project_id": project_id,
            "project_name": project_name,
            "previous_score": round(previous_score, 3),
            "current_score": round(current_score, 3),
            "threshold": HEALTH_CRITICAL_THRESHOLD,
            "severity": "critical",
            "trigger": "crossed_below",
            "message": f"Project health dropped to critical ({current_score:.0%})",
            "recommended_actions": prediction.get("risk_factors", []),
            "detected_at": now,
        }
        alerts.append(alert)
        agent.logger.warning(
            "Health critical threshold crossed for project %s: %.3f -> %.3f",
            project_id,
            previous_score,
            current_score,
        )

    # Check warning threshold crossing
    elif current_score < HEALTH_WARNING_THRESHOLD and previous_score >= HEALTH_WARNING_THRESHOLD:
        alert = {
            "alert_id": await generate_prediction_id(),
            "project_id": project_id,
            "project_name": project_name,
            "previous_score": round(previous_score, 3),
            "current_score": round(current_score, 3),
            "threshold": HEALTH_WARNING_THRESHOLD,
            "severity": "warning",
            "trigger": "crossed_below",
            "message": f"Project health dropped below warning level ({current_score:.0%})",
            "recommended_actions": prediction.get("risk_factors", []),
            "detected_at": now,
        }
        alerts.append(alert)

    # Check rapid decline
    if previous_score - current_score > HEALTH_RAPID_DECLINE_DELTA:
        alert = {
            "alert_id": await generate_prediction_id(),
            "project_id": project_id,
            "project_name": project_name,
            "previous_score": round(previous_score, 3),
            "current_score": round(current_score, 3),
            "threshold": HEALTH_RAPID_DECLINE_DELTA,
            "severity": "warning",
            "trigger": "rapid_decline",
            "message": (
                f"Rapid health decline detected: "
                f"{previous_score:.0%} -> {current_score:.0%} "
                f"(delta {previous_score - current_score:.0%})"
            ),
            "recommended_actions": [
                "Investigate root cause of rapid decline",
                "Review recent scope or resource changes",
                "Schedule risk review meeting",
            ],
            "detected_at": now,
        }
        alerts.append(alert)

    # Publish alert events
    if hasattr(agent, "event_bus") and agent.event_bus and alerts:
        for alert in alerts:
            await agent.event_bus.publish(
                "project.health.alert",
                {
                    "tenant_id": tenant_id,
                    "project_id": project_id,
                    "alert": alert,
                },
            )

    return alerts


async def _calculate_confidence_interval(
    prediction: dict[str, Any], model_type: str
) -> dict[str, float]:
    """Calculate prediction confidence interval."""
    value = prediction.get("value", 0.0)
    confidence = prediction.get("confidence", 0.8)

    if model_type == "health_score":
        # Tighter interval for higher confidence predictions
        half_width = value * (1 - confidence) * 0.5
        return {
            "lower": round(max(0.0, value - half_width), 4),
            "upper": round(min(1.0, value + half_width), 4),
        }

    return {"lower": value * 0.9, "upper": value * 1.1}


async def _generate_prediction_recommendations(
    prediction: dict[str, Any], model_type: str = ""
) -> list[str]:
    """Generate recommendations based on prediction."""
    if model_type != "health_score":
        return ["Monitor actual values against prediction"]

    recommendations: list[str] = []
    value = prediction.get("value", 1.0)
    trend = prediction.get("trend", "stable")

    if value < HEALTH_CRITICAL_THRESHOLD:
        recommendations.append("Escalate to program management for immediate intervention")
        recommendations.append("Conduct root cause analysis on failing health dimensions")
    elif value < HEALTH_WARNING_THRESHOLD:
        recommendations.append("Schedule health review with project team")
        recommendations.append("Identify and address top contributing risk factors")

    if trend == "rapidly_declining":
        recommendations.append("Initiate trend reversal action plan within 48 hours")
    elif trend == "declining":
        recommendations.append("Monitor closely and prepare mitigation strategies")
    elif trend == "improving":
        recommendations.append("Continue current trajectory; document lessons learned")

    breakdown = prediction.get("breakdown", {})
    if breakdown.get("schedule_score", 1.0) < 0.4:
        recommendations.append("Re-baseline schedule with realistic estimates")
    if breakdown.get("budget_score", 1.0) < 0.4:
        recommendations.append("Review budget allocation and forecast to completion")
    if breakdown.get("resource_score", 1.0) < 0.4:
        recommendations.append("Assess resource capacity and rebalance assignments")
    if breakdown.get("risk_score", 0.0) > 0.7:
        recommendations.append("Prioritize risk mitigation actions for top-ranked risks")

    if not recommendations:
        recommendations.append("Monitor actual values against prediction")

    return recommendations
