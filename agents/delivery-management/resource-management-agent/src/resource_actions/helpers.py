"""Internal helper functions for the ResourceCapacityAgent.

These functions implement the business logic for capacity calculations,
performance scoring, allocation validation, skill indexing, scenario
modelling and other cross-cutting concerns.  They all accept an ``agent``
instance as their first argument so they can read/write agent state.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from resource_models import EmbeddingClient, TimeSeriesForecaster
from resource_utils import (
    calculate_performance_score_from_records,
    get_effective_skills,
    normalized_skill_match_weights,
)

if TYPE_CHECKING:
    from resource_capacity_agent import ResourceCapacityAgent


# ---------------------------------------------------------------------------
# Skill indexing
# ---------------------------------------------------------------------------


async def index_skills(agent: ResourceCapacityAgent) -> None:
    """Upload skill embeddings for every resource to Azure AI Search."""
    if not agent.search_client or not agent.search_client.is_configured():
        return
    documents = []
    embedding_client = agent.embedding_client or EmbeddingClient(None, None, None)
    for resource_id, resource in agent.resource_pool.items():
        skills_text = " ".join(get_effective_skills(resource))
        documents.append(
            {
                "@search.action": "mergeOrUpload",
                "resource_id": resource_id,
                "skills": skills_text,
                "role": resource.get("role"),
                "availability": resource.get("availability", 1.0),
                "cost_rate": resource.get("cost_rate", 0.0),
                "embedding": embedding_client.get_embedding(skills_text),
            }
        )
    agent.search_client.upload_documents(documents)
    agent._skills_indexed = True


# ---------------------------------------------------------------------------
# ML model training
# ---------------------------------------------------------------------------


async def train_forecasting_models(
    agent: ResourceCapacityAgent,
    capacity_series: list[float],
    demand_series: list[float],
    *,
    tenant_id: str,
    history_months: int,
) -> dict[str, Any]:
    """Train Azure ML capacity and demand forecast models; return metadata."""
    if not agent.ml_forecast_client or not agent.ml_forecast_client.is_configured():
        return {}
    run_id = f"forecast-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    metadata: dict[str, Any] = {
        "run_id": run_id,
        "tenant_id": tenant_id,
        "history_months": history_months,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    capacity_model_name = f"{tenant_id}-capacity"
    demand_model_name = f"{tenant_id}-demand"
    capacity_info = agent.ml_forecast_client.train_model(
        capacity_model_name,
        capacity_series,
        agent.forecast_horizon_months,
        metadata={"series_type": "capacity", **metadata},
    )
    demand_info = agent.ml_forecast_client.train_model(
        demand_model_name,
        demand_series,
        agent.forecast_horizon_months,
        metadata={"series_type": "demand", **metadata},
    )
    metadata["capacity_model"] = capacity_info
    metadata["demand_model"] = demand_info
    if agent.db_service:
        await agent.db_service.store("capacity_forecast_models", run_id, metadata)
    if capacity_info:
        await store_model_in_azure_ml(agent, capacity_model_name, capacity_info)
    if demand_info:
        await store_model_in_azure_ml(agent, demand_model_name, demand_info)
    return metadata


async def store_model_in_azure_ml(
    agent: ResourceCapacityAgent, model_name: str, model: dict[str, Any]
) -> None:
    """Register a trained model in Azure ML."""
    endpoint = os.getenv("AZURE_ML_ENDPOINT")
    api_key = os.getenv("AZURE_ML_API_KEY")
    if not endpoint or not api_key:
        return
    try:
        import requests

        response = requests.post(
            f"{endpoint}/models/register",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"name": model_name, "model": model},
            timeout=30,
        )
        response.raise_for_status()
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ) as exc:
        agent.logger.warning("Azure ML model registration failed", extra={"error": str(exc)})


# ---------------------------------------------------------------------------
# Capacity/demand calculations
# ---------------------------------------------------------------------------


async def calculate_total_capacity(agent: ResourceCapacityAgent) -> float:
    """Sum FTE availability across all active resources."""
    total_capacity = 0.0
    for resource in agent.resource_pool.values():
        if resource.get("status") != "Active":
            continue
        total_capacity += float(resource.get("availability", 0.0))
    return total_capacity


async def calculate_total_demand(
    agent: ResourceCapacityAgent, risk_data: dict[str, Any] | None = None
) -> float:
    """Sum FTE demand from all active allocations, adjusted for risk load."""
    total_demand = 0.0
    for allocations_list in agent.allocations.values():
        for alloc in allocations_list:
            if alloc.get("status") == "Active":
                base_allocation = float(alloc.get("allocation_percentage", 0) or 0) / 100
                risk_level = agent._resolve_allocation_risk_level(alloc, risk_data)
                total_demand += base_allocation * agent._risk_load_factor(risk_level)
    return total_demand


async def build_capacity_demand_history(
    agent: ResourceCapacityAgent, months: int
) -> tuple[list[float], list[float]]:
    """Build historical capacity and demand time-series for forecasting."""
    if months <= 0:
        return [], []
    now = datetime.now(timezone.utc)
    capacity_value = await calculate_total_capacity(agent)
    capacity_series: list[float] = []
    demand_series: list[float] = []
    for offset in range(-months + 1, 1):
        ms = agent._month_start(now, offset)
        me = agent._month_start(now, offset + 1) - timedelta(days=1)
        month_days = max((me - ms).days + 1, 1)
        month_demand = 0.0
        for allocations_list in agent.allocations.values():
            for alloc in allocations_list:
                if alloc.get("status") != "Active":
                    continue
                alloc_start_str = alloc.get("start_date")
                alloc_end_str = alloc.get("end_date")
                if not isinstance(alloc_start_str, str) or not isinstance(alloc_end_str, str):
                    continue
                alloc_start = datetime.fromisoformat(alloc_start_str)
                alloc_end = datetime.fromisoformat(alloc_end_str)
                if alloc_end < ms or alloc_start > me:
                    continue
                overlap_start = max(alloc_start, ms)
                overlap_end = min(alloc_end, me)
                overlap_days = max((overlap_end - overlap_start).days + 1, 0)
                allocation_fte = float(alloc.get("allocation_percentage", 0)) / 100
                month_demand += allocation_fte * (overlap_days / month_days)
        capacity_series.append(capacity_value)
        demand_series.append(month_demand)
    return capacity_series, demand_series


# ---------------------------------------------------------------------------
# Scenario helpers
# ---------------------------------------------------------------------------


async def create_baseline_scenario(agent: ResourceCapacityAgent) -> dict[str, Any]:
    """Build the baseline scenario snapshot for what-if analysis."""
    from resource_actions.planning import handle_forecast_capacity

    history_months = 6
    cap_series, dem_series = await build_capacity_demand_history(agent, history_months)
    forecast = await handle_forecast_capacity(agent, {"history_months": history_months})
    utilization = await calculate_total_demand(agent)
    total_capacity = await calculate_total_capacity(agent)
    return {
        "resource_count": len(agent.resource_pool),
        "allocations": agent.allocations,
        "utilization": utilization / total_capacity if total_capacity else 0.0,
        "capacity_series": cap_series,
        "demand_series": dem_series,
        "forecast": forecast,
        "average_cost_rate": average_cost_rate(agent),
    }


async def forecast_capacity_for_scenario(
    agent: ResourceCapacityAgent, scenario: dict[str, Any]
) -> dict[str, Any]:
    """Run a time-series forecast with scenario-adjusted capacity/demand series."""
    history_months = 6
    cap_series, dem_series = await build_capacity_demand_history(agent, history_months)
    scope_multiplier = float(scenario.get("scope_multiplier", 1.0))
    capacity_multiplier = float(scenario.get("capacity_multiplier", 1.0))
    resource_count = int(scenario.get("resource_count", len(agent.resource_pool)))
    base_count = len(agent.resource_pool) or 1
    adj_cap = [value * (resource_count / base_count) * capacity_multiplier for value in cap_series]
    adj_dem = [value * scope_multiplier for value in dem_series]
    forecaster = TimeSeriesForecaster(
        automl_endpoint=os.getenv("AZURE_AUTOML_ENDPOINT"),
        automl_api_key=os.getenv("AZURE_AUTOML_API_KEY"),
    )
    cap_forecast = forecaster.forecast(adj_cap, agent.forecast_horizon_months)
    dem_forecast = forecaster.forecast(adj_dem, agent.forecast_horizon_months)
    return {
        "future_capacity": [
            {"month": i + 1, "capacity": max(0.0, v)} for i, v in enumerate(cap_forecast)
        ],
        "future_demand": [
            {"month": i + 1, "demand": max(0.0, v)} for i, v in enumerate(dem_forecast)
        ],
    }


# ---------------------------------------------------------------------------
# Resource matching
# ---------------------------------------------------------------------------


async def find_matching_resources(
    agent: ResourceCapacityAgent,
    skills_required: list[str],
    *,
    availability_floor: float = 0.0,
) -> list[dict[str, Any]]:
    """Score and rank resources against required skills using weighted criteria."""
    required_skills = {skill.lower() for skill in skills_required if skill}
    max_cost = max(
        (float(r.get("cost_rate", 0)) for r in agent.resource_pool.values()),
        default=0.0,
    )
    weights = normalized_skill_match_weights(agent.skill_match_weights)

    matches: list[dict[str, Any]] = []
    for resource_id, resource in agent.resource_pool.items():
        resource_skills = {skill.lower() for skill in get_effective_skills(resource) if skill}
        skill_score = (
            len(resource_skills.intersection(required_skills)) / len(required_skills)
            if required_skills
            else 1.0
        )
        availability_score = float(resource.get("availability", 0.0))
        if availability_score < availability_floor:
            continue
        cost_rate = float(resource.get("cost_rate", 0.0))
        cost_score = 1.0 - (cost_rate / max_cost) if max_cost else 1.0
        performance_score = await get_performance_score(agent, resource_id, {})

        weighted_score = (
            weights["skills"] * skill_score
            + weights["availability"] * availability_score
            + weights["cost"] * cost_score
            + weights["performance"] * performance_score
        )
        matches.append(
            {
                "resource_id": resource_id,
                "resource_name": resource.get("name"),
                "role": resource.get("role"),
                "skills": list(resource_skills),
                "match_score": skill_score,
                "availability_score": availability_score,
                "cost_score": cost_score,
                "performance_score": performance_score,
                "weighted_score": weighted_score,
            }
        )

    matches.sort(key=lambda item: item["weighted_score"], reverse=True)
    return matches


# ---------------------------------------------------------------------------
# Performance scoring
# ---------------------------------------------------------------------------


async def get_performance_score(
    agent: ResourceCapacityAgent,
    resource_id: str,
    project_context: dict[str, Any],
) -> float:
    """Retrieve (or compute and cache) the performance score for a resource."""
    if resource_id in agent.performance_scores:
        return agent.performance_scores[resource_id]
    if agent.redis_client:
        cached = agent.redis_client.get(f"resource_performance:{resource_id}")
        if cached:
            try:
                score = float(cached)
                agent.performance_scores[resource_id] = score
                return score
            except ValueError:
                pass
    score = 0.85
    if agent.db_service:
        records = await agent.db_service.query(
            "project_performance", {"resource_id": resource_id}, limit=50
        )
        if records:
            score = calculate_performance_score_from_records(
                records, project_context, agent.analytics_client
            )
    agent.performance_scores[resource_id] = score
    if agent.db_service:
        await agent.db_service.store(
            "resource_performance_scores",
            resource_id,
            {
                "resource_id": resource_id,
                "score": score,
                "calculated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    agent.repository.upsert_performance_score(
        resource_id, score, {"calculated_at": datetime.now(timezone.utc).isoformat()}
    )
    if agent.redis_client:
        agent.redis_client.set(f"resource_performance:{resource_id}", score, ex=3600)
    return score


# ---------------------------------------------------------------------------
# Allocation helpers
# ---------------------------------------------------------------------------


async def validate_allocation(
    agent: ResourceCapacityAgent,
    resource_id: str,
    start_date: str,
    end_date: str,
    allocation_percentage: float,
) -> dict[str, Any]:
    """Validate an allocation request against pool constraints."""
    if resource_id not in agent.resource_pool:
        return {"valid": False, "reason": "Resource not found"}
    if allocation_percentage <= 0 or allocation_percentage > 100:
        return {"valid": False, "reason": "Invalid allocation percentage"}

    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    allocations = agent._load_allocations(resource_id)
    total_overlap = allocation_percentage
    overlapping_allocations = 0
    for alloc in allocations:
        overlap = await check_allocation_overlap(
            alloc, {"start_date": start_date, "end_date": end_date}
        )
        if overlap.get("has_overlap"):
            overlapping_allocations += 1
            total_overlap += float(alloc.get("allocation_percentage", 0))
    if (
        agent.enforce_allocation_constraints
        and overlapping_allocations >= agent.max_concurrent_allocations
    ):
        return {
            "valid": False,
            "reason": "Allocation exceeds maximum concurrent allocation constraint",
        }
    if total_overlap > (agent.max_allocation_threshold * 100):
        return {"valid": False, "reason": "Allocation exceeds maximum capacity threshold"}
    if start > end:
        return {"valid": False, "reason": "Start date must be before end date"}
    return {"valid": True}


async def check_allocation_overlap(
    alloc1: dict[str, Any], alloc2: dict[str, Any]
) -> dict[str, Any]:
    """Return overlap details for two allocation date ranges."""
    start1_str = alloc1.get("start_date")
    end1_str = alloc1.get("end_date")
    start2_str = alloc2.get("start_date")
    end2_str = alloc2.get("end_date")
    assert isinstance(start1_str, str) and isinstance(end1_str, str), "alloc1 dates must be strings"
    assert isinstance(start2_str, str) and isinstance(end2_str, str), "alloc2 dates must be strings"
    start1 = datetime.fromisoformat(start1_str)
    end1 = datetime.fromisoformat(end1_str)
    start2 = datetime.fromisoformat(start2_str)
    end2 = datetime.fromisoformat(end2_str)

    has_overlap = not (end1 < start2 or end2 < start1)
    if has_overlap:
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)
        return {
            "has_overlap": True,
            "period": {"start": overlap_start.isoformat(), "end": overlap_end.isoformat()},
        }
    return {"has_overlap": False}


async def update_resource_availability(agent: ResourceCapacityAgent, resource_id: str) -> None:
    """Recalculate and persist availability after an allocation change."""
    allocations = agent.allocations.get(resource_id, [])
    total_allocation = sum(
        alloc.get("allocation_percentage", 0)
        for alloc in allocations
        if alloc.get("status") == "Active"
    )
    availability = max(0, 100 - total_allocation) / 100
    training_load = float(agent.resource_pool.get(resource_id, {}).get("training_load", 0.0))
    availability = max(0.0, availability - training_load)
    agent.resource_pool[resource_id]["availability"] = availability
    schedule = agent.capacity_calendar.get(resource_id, {})
    await agent._persist_resource_schedule(
        resource_id,
        schedule,
        tenant_id=agent.default_tenant_id,
        availability=availability,
    )
    if agent.db_service:
        await agent.db_service.store(
            "resource_availability",
            resource_id,
            {
                "resource_id": resource_id,
                "availability": availability,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )


async def calculate_day_availability(
    agent: ResourceCapacityAgent,
    resource_id: str,
    date: datetime,
    calendar: dict[str, Any],
    allocations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return available hours for a resource on a given calendar day."""
    weekday = date.weekday()
    if weekday not in calendar.get("working_days", []):
        return {"date": date.isoformat(), "available_hours": 0, "reason": "Non-working day"}

    total_hours = calendar.get("available_hours_per_day", agent.default_working_hours_per_day)
    date_str = date.date().isoformat()
    holidays = {str(day) for day in calendar.get("holidays", [])}
    if date_str in holidays:
        return {
            "date": date.isoformat(),
            "total_hours": total_hours,
            "available_hours": 0,
            "reason": "Holiday",
        }
    for leave in calendar.get("planned_leave", []):
        start_str = leave.get("start_date")
        end_str = leave.get("end_date")
        if not isinstance(start_str, str) or not isinstance(end_str, str):
            continue
        leave_start = datetime.fromisoformat(start_str)
        leave_end = datetime.fromisoformat(end_str)
        if leave_start.date() <= date.date() <= leave_end.date():
            leave_hours = float(leave.get("hours", total_hours))
            available_hours = max(0.0, total_hours - leave_hours)
            return {
                "date": date.isoformat(),
                "total_hours": total_hours,
                "available_hours": available_hours,
                "reason": leave.get("reason", "Planned leave"),
            }

    allocated_hours = 0.0
    for alloc in allocations:
        alloc_start_str = alloc.get("start_date")
        alloc_end_str = alloc.get("end_date")
        if not isinstance(alloc_start_str, str) or not isinstance(alloc_end_str, str):
            continue
        alloc_start = datetime.fromisoformat(alloc_start_str)
        alloc_end = datetime.fromisoformat(alloc_end_str)
        if alloc_start <= date <= alloc_end:
            daily_hours = calendar.get("available_hours_per_day", 8)
            allocated_hours += daily_hours * (alloc.get("allocation_percentage", 0) / 100)

    total_hours = calendar.get("available_hours_per_day", agent.default_working_hours_per_day)
    available_hours = max(0.0, total_hours - allocated_hours)
    return {
        "date": date.isoformat(),
        "total_hours": total_hours,
        "allocated_hours": allocated_hours,
        "available_hours": available_hours,
    }


# ---------------------------------------------------------------------------
# Approval routing
# ---------------------------------------------------------------------------


async def determine_approver(agent: ResourceCapacityAgent, request: dict[str, Any]) -> str:
    """Determine the appropriate approver for a resource request."""
    default_approver = agent.approval_routing.get("default_approver", "resource_manager")
    requester = request.get("requested_by")
    requester_profile = agent.org_structure.get(requester, {}) if requester else {}
    if requester_profile.get("manager"):
        return requester_profile["manager"]
    project_role = request.get("project_role") or request.get("role")
    if project_role:
        mapping = agent.approval_routing.get("by_project_role", {})
        if project_role in mapping:
            return mapping[project_role]
    for role in request.get("project_roles", []) or []:
        mapping = agent.approval_routing.get("by_project_role", {})
        if role in mapping:
            return mapping[role]
    project_id = request.get("project_id")
    if project_id:
        mapping = agent.approval_routing.get("by_project", {})
        if project_id in mapping:
            return mapping[project_id]
    department = request.get("department") or requester_profile.get("department")
    if department:
        mapping = agent.approval_routing.get("by_department", {})
        if department in mapping:
            return mapping[department]
    role = request.get("role") or requester_profile.get("role")
    if role:
        mapping = agent.approval_routing.get("by_role", {})
        if role in mapping:
            return mapping[role]
    effort = float(request.get("effort", 0))
    for threshold in sorted(
        agent.approval_routing.get("effort_thresholds", []),
        key=lambda item: float(item.get("threshold", 0)),
        reverse=True,
    ):
        if effort >= float(threshold.get("threshold", 0)):
            return threshold.get("approver", default_approver)
    return default_approver


# ---------------------------------------------------------------------------
# Training record helpers
# ---------------------------------------------------------------------------


async def apply_training_record(
    agent: ResourceCapacityAgent, resource_id: str, record: dict[str, Any]
) -> dict[str, Any]:
    """Apply a training record to a resource, updating skills and availability."""
    from resource_utils import calculate_training_load

    resource = agent.resource_pool.get(resource_id)
    if not resource:
        return {}
    completed = record.get("completed", [])
    in_progress = record.get("in_progress", [])
    scheduled = record.get("scheduled", [])
    certifications = record.get("certifications", [])
    skills = record.get("skills", [])
    training_load = calculate_training_load(
        record, agent.default_working_hours_per_day, agent.default_working_days
    )
    training_metadata = {
        "completed": completed,
        "in_progress": in_progress,
        "scheduled": scheduled,
        "certifications": certifications,
        "skills": skills,
        "training_load": training_load,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    resource["training"] = training_metadata
    resource["training_load"] = training_load
    resource["certifications"] = list(
        {*(resource.get("certifications", []) or []), *certifications}
    )
    resource["skills"] = list({*(resource.get("skills", []) or []), *skills})
    if agent.db_service:
        await agent.db_service.store(
            "resource_training",
            resource_id,
            {"resource_id": resource_id, **training_metadata},
        )
    await update_resource_availability(agent, resource_id)
    return training_metadata


# ---------------------------------------------------------------------------
# Optimisation
# ---------------------------------------------------------------------------


async def optimize_resource_allocations(
    agent: ResourceCapacityAgent, planning_horizon: dict[str, Any]
) -> dict[str, Any]:
    """Greedy resource-to-request assignment optimiser."""
    if not agent.resource_optimization_enabled:
        return {
            "status": "disabled",
            "reason": "resource_optimization feature flag is disabled",
            "constraints": {"feature_flag": "resource_optimization", "enabled": False},
            "scoring": {},
            "proposed_allocations": [],
            "unfilled_requests": [],
            "remaining_capacity": {},
        }
    pending_requests = [
        req for req in agent.demand_requests.values() if req.get("status") == "Pending"
    ]
    pending_requests.extend(planning_horizon.get("requests", []))
    pending_requests.sort(key=lambda req: (-(req.get("effort", 1.0)), req.get("start_date", "")))

    availability = {
        rid: float(r.get("availability", 0.0)) for rid, r in agent.resource_pool.items()
    }
    allocations_list: list[dict[str, Any]] = []
    unfilled: list[dict[str, Any]] = []
    weights = normalized_skill_match_weights(agent.skill_match_weights)
    constraints = {
        "availability_floor_policy": "effort",
        "max_concurrent_allocations": agent.max_concurrent_allocations,
        "max_allocation_threshold": agent.max_allocation_threshold,
        "enforce_allocation_constraints": agent.enforce_allocation_constraints,
        "utilization_target": agent.utilization_target,
        "resource_pool_size": len(agent.resource_pool),
        "request_count": len(pending_requests),
    }

    for request in pending_requests:
        required_skills = request.get("required_skills", [])
        effort = float(request.get("effort", 1.0))
        request_id = request.get("request_id") or request.get("id") or "pending"
        matches = await find_matching_resources(agent, required_skills, availability_floor=effort)
        assigned = False
        for match in matches:
            resource_id = match["resource_id"]
            if availability.get(resource_id, 0.0) >= effort:
                availability[resource_id] = max(0.0, availability.get(resource_id, 0.0) - effort)
                matched_skills = set(match.get("skills", []))
                required_skill_set = {s for s in required_skills if s}
                rationale = [
                    f"Matched {len(matched_skills.intersection(required_skill_set))} of "
                    f"{len(required_skill_set)} required skills.",
                    f"Availability score {match.get('availability_score'):.2f} meets effort "
                    f"threshold {effort:.2f}.",
                    f"Weighted score {match.get('weighted_score', 0.0):.2f} using configured "
                    "skill, availability, cost, and performance weights.",
                ]
                allocations_list.append(
                    {
                        "request_id": request_id,
                        "resource_id": resource_id,
                        "score": match.get("weighted_score"),
                        "effort": effort,
                        "rationale": rationale,
                        "scoring": {
                            "weighted_score": match.get("weighted_score"),
                            "components": {
                                "skills": match.get("match_score"),
                                "availability": match.get("availability_score"),
                                "cost": match.get("cost_score"),
                                "performance": match.get("performance_score"),
                            },
                            "weights": weights,
                        },
                    }
                )
                assigned = True
                break
        if not assigned:
            unfilled.append(
                {
                    "request_id": request_id,
                    "required_skills": required_skills,
                    "effort": effort,
                    "rationale": "No available resources met the skill or effort constraints.",
                }
            )

    return {
        "proposed_allocations": allocations_list,
        "unfilled_requests": unfilled,
        "remaining_capacity": availability,
        "constraints": constraints,
        "scoring": {"method": "weighted_skill_match", "weights": weights},
    }


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------


def average_cost_rate(agent: ResourceCapacityAgent) -> float:
    """Compute the mean cost rate across the resource pool."""
    if not agent.resource_pool:
        return 0.0
    return sum(float(r.get("cost_rate", 0.0)) for r in agent.resource_pool.values()) / len(
        agent.resource_pool
    )


async def store_canonical_profile(
    agent: ResourceCapacityAgent,
    resource_id: str,
    canonical_profile: dict[str, Any],
    resource_profile: dict[str, Any],
) -> None:
    """Persist the canonical (employee) and resource profiles to all stores."""
    agent.repository.upsert_employee_profile(canonical_profile)
    if agent.db_service:
        await agent.db_service.store("employee_profiles", resource_id, canonical_profile)
        await agent.db_service.store("resource_profiles", resource_id, resource_profile)


async def generate_conflict_recommendations(
    conflicts: list[dict[str, Any]],
) -> list[str]:
    """Build human-readable recommendations for detected allocation conflicts."""
    recommendations = []
    for conflict in conflicts:
        if conflict.get("severity") == "high":
            recommendations.append(
                f"Critical: Resource {conflict.get('resource_name')} is over-allocated by "
                f"{conflict.get('over_allocation_percentage')}%. "
                "Consider reallocating or adding resources."
            )
    return recommendations


# ---------------------------------------------------------------------------
# Forecast adjustment helpers
# ---------------------------------------------------------------------------


def training_capacity_adjustments(agent: ResourceCapacityAgent, horizon: int) -> list[float]:
    """Compute per-month capacity reduction due to scheduled training sessions."""
    adjustments = [0.0] * horizon
    total_work_hours = agent.default_working_hours_per_day * len(agent.default_working_days)
    if total_work_hours == 0:
        return adjustments
    now = datetime.now(timezone.utc)
    for record in agent.training_records.values():
        for session in record.get("scheduled", []) or []:
            date_str = session.get("date")
            hours = float(session.get("hours", 0.0))
            if not date_str:
                continue
            session_date = datetime.fromisoformat(date_str)
            month_offset = (session_date.year - now.year) * 12 + session_date.month - now.month
            if 0 <= month_offset < horizon:
                adjustments[month_offset] += hours / max(total_work_hours, 1.0)
    return [value * agent.training_capacity_impact for value in adjustments]


def pipeline_demand_adjustments(agent: ResourceCapacityAgent, horizon: int) -> list[float]:
    """Compute per-month demand additions from the configured pipeline forecast."""
    adjustments = [0.0] * horizon
    pipeline = agent.config.get("pipeline_forecast", []) if agent.config else []
    for entry in pipeline:
        month = int(entry.get("month", 0)) - 1
        demand = float(entry.get("demand", 0.0))
        if 0 <= month < horizon:
            adjustments[month] += demand
    return adjustments


def skill_development_multiplier(agent: ResourceCapacityAgent) -> float:
    """Compute an uplift multiplier based on completed training across the pool."""
    if not agent.training_records:
        return 1.0
    completed_count = sum(
        len(record.get("completed", []) or []) for record in agent.training_records.values()
    )
    resource_count = max(len(agent.resource_pool), 1)
    uplift = min(agent.skill_development_uplift, completed_count / (resource_count * 10))
    return 1.0 + uplift


def seasonality_multiplier(agent: ResourceCapacityAgent, month_offset: int) -> float:
    """Return the seasonality factor for a given month offset from now."""
    now = datetime.now(timezone.utc)
    target_month = (now.month - 1 + month_offset) % 12 + 1
    return float(agent.seasonality_factors.get(str(target_month), 1.0))


def adjust_capacity_forecast(
    agent: ResourceCapacityAgent, forecast: list[float]
) -> list[dict[str, Any]]:
    """Apply attrition, training, and seasonality adjustments to a capacity forecast."""
    attrition_rate = agent.attrition_rate or 0.0
    training_adj = training_capacity_adjustments(agent, len(forecast))
    uplift = skill_development_multiplier(agent)
    return [
        {
            "month": index + 1,
            "capacity": max(
                0.0,
                (value * (1 - attrition_rate) * seasonality_multiplier(agent, index) * uplift)
                - training_adj[index],
            ),
        }
        for index, value in enumerate(forecast)
    ]


def adjust_demand_forecast(
    agent: ResourceCapacityAgent, forecast: list[float]
) -> list[dict[str, Any]]:
    """Apply pipeline and seasonality adjustments to a demand forecast."""
    pipeline_adj = pipeline_demand_adjustments(agent, len(forecast))
    return [
        {
            "month": index + 1,
            "demand": max(
                0.0,
                (value + pipeline_adj[index]) * seasonality_multiplier(agent, index),
            ),
        }
        for index, value in enumerate(forecast)
    ]


# ---------------------------------------------------------------------------
# Risk adjustment helpers
# ---------------------------------------------------------------------------


def load_risk_adjustments_config(
    agent: ResourceCapacityAgent,
) -> dict[str, dict[str, float]]:
    """Load risk adjustment config from YAML; fall back to hard-coded defaults."""
    import yaml

    defaults: dict[str, dict[str, float]] = {
        "high": {"schedule_buffer_pct": 0.2, "resource_load_factor": 1.25},
        "medium": {"schedule_buffer_pct": 0.1, "resource_load_factor": 1.1},
        "low": {"schedule_buffer_pct": 0.05, "resource_load_factor": 1.0},
        "default": {"schedule_buffer_pct": 0.0, "resource_load_factor": 1.0},
    }
    if not agent.risk_adjustments_path.exists():
        return defaults
    try:
        payload = yaml.safe_load(agent.risk_adjustments_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError, ValueError):
        return defaults
    configured = payload.get("risk_adjustments", {}) if isinstance(payload, dict) else {}
    normalized: dict[str, dict[str, float]] = {}
    for level, values in configured.items():
        if not isinstance(values, dict):
            continue
        normalized[str(level).lower()] = {
            "schedule_buffer_pct": float(values.get("schedule_buffer_pct", 0.0) or 0.0),
            "resource_load_factor": float(values.get("resource_load_factor", 1.0) or 1.0),
        }
    return {**defaults, **normalized}


def build_risk_capacity_recommendations(
    risk_data: dict[str, Any] | None,
) -> list[str]:
    """Build capacity recommendations based on project risk level."""
    if not risk_data:
        return []
    project_level = str(risk_data.get("project_risk_level", "low")).lower()
    recommendations: list[str] = []
    if project_level == "high":
        recommendations.append(
            "Increase capacity buffers or add contingency staff for high-risk scope."
        )
        recommendations.append(
            "Apply schedule padding for high-risk tasks to reduce burnout and overruns."
        )
    elif project_level == "medium":
        recommendations.append(
            "Monitor utilization weekly and reserve partial contingency capacity."
        )
    return recommendations


def merge_profiles(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge profiles from multiple HR sources, deduplicating by employee ID/email/name."""
    merged: dict[str, dict[str, Any]] = {}
    for profile in profiles:
        key = (
            profile.get("employee_id")
            or profile.get("email")
            or profile.get("name")
            or str(uuid.uuid4())
        )
        existing = merged.get(key, {})
        combined = {**existing, **{k: v for k, v in profile.items() if v}}
        combined["employee_id"] = combined.get("employee_id") or key
        merged[key] = combined
    return list(merged.values())
