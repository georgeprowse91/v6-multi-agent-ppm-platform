"""Action handlers: forecast_capacity, plan_capacity, scenario_analysis."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast

from resource_models import TimeSeriesForecaster

from resource_actions.helpers import (
    build_capacity_demand_history,
    calculate_total_capacity,
    calculate_total_demand,
    create_baseline_scenario,
    optimize_resource_allocations,
    train_forecasting_models,
)

if TYPE_CHECKING:
    from resource_capacity_agent import ResourceCapacityAgent


async def handle_forecast_capacity(
    agent: ResourceCapacityAgent,
    filters: dict[str, Any],
) -> dict[str, Any]:
    """
    Forecast future capacity vs demand.

    Returns capacity forecast with bottlenecks.
    """
    agent.logger.info("Forecasting capacity")

    history_months = int(filters.get("history_months", 6))
    tenant_id = filters.get("tenant_id") or agent.default_tenant_id
    cache_key = f"capacity_forecast:{tenant_id}:{history_months}:{agent.forecast_horizon_months}"
    if agent.redis_client:
        cached = agent.redis_client.get(cache_key)
        if cached:
            try:
                return cast(dict[str, Any], json.loads(cached))
            except json.JSONDecodeError:
                pass

    # Calculate current capacity and demand
    current_capacity = await calculate_total_capacity(agent)
    risk_data = filters.get("risk_data") if isinstance(filters.get("risk_data"), dict) else None
    current_demand = await calculate_total_demand(agent, risk_data)

    capacity_series, demand_series = await build_capacity_demand_history(agent, history_months)
    ml_metadata = await train_forecasting_models(
        agent, capacity_series, demand_series, tenant_id=tenant_id, history_months=history_months
    )
    capacity_forecast = None
    demand_forecast = None
    if agent.ml_forecast_client and agent.ml_forecast_client.is_configured():
        capacity_forecast = agent.ml_forecast_client.forecast(
            f"{tenant_id}-capacity", capacity_series, agent.forecast_horizon_months
        )
        demand_forecast = agent.ml_forecast_client.forecast(
            f"{tenant_id}-demand", demand_series, agent.forecast_horizon_months
        )
    if capacity_forecast is None or demand_forecast is None:
        forecaster = TimeSeriesForecaster(
            automl_endpoint=os.getenv("AZURE_AUTOML_ENDPOINT"),
            automl_api_key=os.getenv("AZURE_AUTOML_API_KEY"),
        )
        capacity_forecast = forecaster.forecast(capacity_series, agent.forecast_horizon_months)
        demand_forecast = forecaster.forecast(demand_series, agent.forecast_horizon_months)
    future_capacity = agent._adjust_capacity_forecast(capacity_forecast)
    future_demand = agent._adjust_demand_forecast(demand_forecast)

    # Identify bottlenecks and generate recommendations
    bottlenecks = await agent._identify_capacity_bottlenecks(future_capacity, future_demand)
    recommendations = await agent._generate_capacity_recommendations(bottlenecks)
    assumptions = {
        "attrition_rate": agent._get_attrition_rate(),
        "seasonality_factors": agent.seasonality_factors,
        "training_capacity_impact": agent.training_capacity_impact,
        "skill_development_uplift": agent.skill_development_uplift,
        "ml_metadata": ml_metadata,
    }
    forecast_payload = {
        "forecast_horizon_months": agent.forecast_horizon_months,
        "current_capacity": current_capacity,
        "current_demand": current_demand,
        "current_utilization": (current_demand / current_capacity if current_capacity > 0 else 0),
        "history": {
            "months": history_months,
            "capacity_series": capacity_series,
            "demand_series": demand_series,
        },
        "future_capacity": future_capacity,
        "future_demand": future_demand,
        "bottlenecks": bottlenecks,
        "recommendations": recommendations,
        "assumptions": assumptions,
        "type": "capacity_vs_demand",
    }
    forecast_id = f"forecast-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    if agent.db_service:
        await agent.db_service.store(
            "capacity_forecasts",
            forecast_id,
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "forecast": forecast_payload,
                "assumptions": assumptions,
            },
        )
    agent.repository.upsert_forecast(forecast_id, forecast_payload)
    await agent._publish_resource_event("resource.capacity.forecasted", forecast_payload)
    if agent.redis_client:
        agent.redis_client.set(cache_key, json.dumps(forecast_payload), ex=900)
    if agent.analytics_client:
        agent.analytics_client.record_metric("capacity.current", current_capacity)
        agent.analytics_client.record_metric("demand.current", current_demand)
        agent.analytics_client.record_metric(
            "utilization.current",
            current_demand / current_capacity if current_capacity else 0.0,
        )

    return forecast_payload


async def handle_plan_capacity(
    agent: ResourceCapacityAgent,
    planning_horizon: dict[str, Any],
) -> dict[str, Any]:
    """
    Create capacity plan.

    Returns capacity plan with allocation strategy.
    """
    agent.logger.info("Planning capacity")

    # Get forecast
    risk_data = (
        planning_horizon.get("risk_data")
        if isinstance(planning_horizon.get("risk_data"), dict)
        else None
    )
    forecast = await handle_forecast_capacity(agent, {"risk_data": risk_data} if risk_data else {})

    # Identify gaps and mitigation strategies
    gaps = await agent._identify_capacity_gaps(forecast)
    strategies = await agent._generate_mitigation_strategies(gaps)
    optimization = await optimize_resource_allocations(agent, planning_horizon)

    # Create capacity plan
    plan = {
        "planning_horizon": planning_horizon,
        "forecast": forecast,
        "gaps": gaps,
        "mitigation_strategies": strategies,
        "optimization": optimization,
        "hiring_recommendations": await agent._generate_hiring_recommendations(gaps),
        "training_recommendations": await agent._generate_training_recommendations(gaps),
        "risk_based_recommendations": agent._build_risk_capacity_recommendations(risk_data),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    return plan


async def handle_scenario_analysis(
    agent: ResourceCapacityAgent,
    scenario_params: dict[str, Any],
) -> dict[str, Any]:
    """
    Perform what-if scenario analysis.

    Returns scenario comparison metrics.
    """
    agent.logger.info("Running scenario analysis")

    scenario_name = scenario_params.get("scenario_name", "Unnamed Scenario")
    changes = scenario_params.get("changes", {})

    baseline = await create_baseline_scenario(agent)
    scenario_output = await agent.scenario_engine.run_scenario(
        baseline=baseline,
        scenario_params=changes,
        scenario_builder=agent._apply_scenario_changes,
        metrics_builder=agent._calculate_scenario_metrics,
        comparison_builder=agent._compare_scenarios,
        recommendation_builder=agent._generate_scenario_recommendation,
    )

    return {
        "scenario_name": scenario_name,
        "scenario_params": scenario_params,
        "baseline_metrics": scenario_output["baseline_metrics"],
        "scenario_metrics": scenario_output["scenario_metrics"],
        "comparison": scenario_output["comparison"],
        "recommendation": scenario_output.get("recommendation"),
    }
