"""Action handler for predictive analytics."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from analytics_utils import generate_prediction_id, get_health_history

if TYPE_CHECKING:
    from analytics_insights_agent import AnalyticsInsightsAgent


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

    return {
        "prediction_id": prediction_id,
        "model_type": model_type,
        "prediction": prediction.get("value"),
        "confidence": prediction.get("confidence"),
        "confidence_interval": confidence_interval,
        "recommendations": await _generate_prediction_recommendations(prediction),
    }


async def _prepare_features(input_data: dict[str, Any], model_type: str) -> list[float]:
    """Prepare features for ML model."""
    features: list[float] = []
    for value in input_data.values():
        if isinstance(value, (int, float)):
            features.append(float(value))
    return features


async def _make_prediction(
    agent: AnalyticsInsightsAgent,
    model: dict[str, Any],
    features: list[float],
    model_type: str,
    input_data: dict[str, Any],
) -> dict[str, Any]:
    """Make prediction using ML model."""
    if hasattr(model, "predict"):
        predicted_value = model.predict([features])[0]
        return {"value": float(predicted_value), "confidence": 0.8}
    if model_type == "health_score":
        project_id = input_data.get("project_id")
        history = await get_health_history(
            agent, input_data.get("tenant_id", "default"), project_id
        )
        if len(history) >= 2:
            last_two = history[-2:]
            delta = last_two[-1]["composite_score"] - last_two[0]["composite_score"]
            prediction_value = max(0.0, min(1.0, last_two[-1]["composite_score"] + delta))
            return {"value": prediction_value, "confidence": 0.75}
        if history:
            return {"value": history[-1]["composite_score"], "confidence": 0.6}
    return {"value": 0.0, "confidence": 0.85}


async def _calculate_confidence_interval(
    prediction: dict[str, Any], model_type: str
) -> dict[str, float]:
    """Calculate prediction confidence interval."""
    value = prediction.get("value", 0.0)
    return {"lower": value * 0.9, "upper": value * 1.1}


async def _generate_prediction_recommendations(prediction: dict[str, Any]) -> list[str]:
    """Generate recommendations based on prediction."""
    return ["Monitor actual values against prediction"]
