"""
Risk Management Agent - Shared utility functions.

Contains helper methods used across multiple action handlers:
ID generation, risk classification, ML feature building, Monte Carlo
simulation, percentile calculation, data storage, event publishing,
external agent communication, event handlers, and more.
"""

from __future__ import annotations

import importlib.util
import json
import os
import random
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib import request as url_request

from data_quality.helpers import validate_against_schema
from data_quality.rules import evaluate_quality_rules

from agents.common.connector_integration import (
    ProjectManagementService,
)
from agents.runtime.src.state_store import TenantStateStore

if TYPE_CHECKING:
    from risk_management_agent import RiskManagementAgent


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------


async def generate_risk_id() -> str:
    """Generate unique risk ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"RISK-{timestamp}"


async def generate_mitigation_plan_id() -> str:
    """Generate unique mitigation plan ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"MIT-{timestamp}"


# ---------------------------------------------------------------------------
# Risk classification & rating helpers
# ---------------------------------------------------------------------------


async def classify_risk_level(agent: RiskManagementAgent, score: float) -> str:
    """Classify risk level based on score."""
    if score >= agent.high_risk_threshold:
        return "High"
    elif score >= 5:
        return "Medium"
    else:
        return "Low"


def map_rating_to_label(rating: Any) -> str:
    rating_map = {1: "low", 2: "low", 3: "medium", 4: "high", 5: "critical"}
    try:
        value = int(float(rating))
    except (TypeError, ValueError):
        return "medium"
    return rating_map.get(value, "medium")


def coerce_rating(value: Any, *, fallback: int) -> int:
    try:
        rating = int(float(value))
    except (TypeError, ValueError):
        return fallback
    return max(1, min(5, rating))


def normalize_risk_category(value: Any, allowed: list[str]) -> str:
    cleaned = str(value or "").strip().lower()
    if cleaned in allowed:
        return cleaned
    if cleaned in {"financial", "budget", "cost"}:
        return "cost"
    if cleaned in {"regulatory", "legal"}:
        return "compliance"
    return "technical"


def risk_signature(risk: dict[str, Any]) -> str:
    title = str(risk.get("title", "")).strip().lower()
    description = str(risk.get("description", "")).strip().lower()
    return f"{title}::{description}"


def extract_sources(snippets: list[str]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    for snippet in snippets:
        match = re.search(r"\((https?://[^)]+)\)", snippet)
        url = match.group(1) if match else ""
        citation = snippet.strip()
        if not url:
            continue
        sources.append({"url": url, "citation": citation})
    return sources


def fallback_risk_classification(
    summary: str, sources: list[dict[str, str]]
) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    for line in [item.strip("- ").strip() for item in summary.splitlines() if item.strip()]:
        category = "compliance" if "regulation" in line.lower() else "technical"
        risks.append(
            {
                "title": line[:80],
                "description": line,
                "category": category,
                "probability": 3,
                "impact": 3,
                "sources": sources,
            }
        )
    return risks


# ---------------------------------------------------------------------------
# Risk assessment helpers
# ---------------------------------------------------------------------------


async def initial_risk_assessment(risk_data: dict[str, Any]) -> dict[str, Any]:
    """Perform initial risk assessment."""
    probability = risk_data.get("probability", 3)
    impact = risk_data.get("impact", 3)
    score = probability * impact
    return {"probability": probability, "impact": impact, "score": score}


async def build_risk_features(agent: RiskManagementAgent, risk: dict[str, Any]) -> dict[str, Any]:
    schedule_distribution = await fetch_schedule_baseline(agent, risk.get("project_id"))
    financial_distribution = await fetch_financial_distribution(agent, risk.get("project_id"))
    schedule_delay = schedule_distribution.get("mean_delay_days", 0) or 0
    cost_overrun = financial_distribution.get("mean_cost_overrun", 0) or 0
    baseline_duration = schedule_distribution.get("baseline_duration_days", 100) or 100
    baseline_cost = financial_distribution.get("baseline_cost", 1_000_000) or 1_000_000

    quality_score = risk.get("quality_score") or risk.get("quality_metrics", {}).get("score")
    resource_utilization = risk.get("resource_utilization") or risk.get("resource_metrics", {}).get(
        "utilization"
    )
    schedule_pressure = float(schedule_delay) / max(1.0, float(baseline_duration))
    cost_pressure = float(cost_overrun) / max(1.0, float(baseline_cost))
    quality_pressure = 1 - (float(quality_score) if quality_score is not None else 0.8)
    resource_pressure = float(resource_utilization) if resource_utilization is not None else 0.7

    return {
        "title": risk.get("title"),
        "description": risk.get("description"),
        "category": risk.get("category"),
        "risk_indicator": risk.get("probability", 3),
        "impact_indicator": risk.get("impact", 3),
        "schedule_pressure": round(schedule_pressure, 4),
        "cost_pressure": round(cost_pressure, 4),
        "quality_pressure": round(quality_pressure, 4),
        "resource_pressure": round(resource_pressure, 4),
        "baseline_duration_days": baseline_duration,
        "baseline_cost": baseline_cost,
    }


async def ensure_local_risk_models(agent: RiskManagementAgent) -> None:
    if agent._local_probability_model and agent._local_impact_model:
        return
    if importlib.util.find_spec("sklearn") is None:
        return
    samples: list[list[float]] = []
    probability_targets: list[float] = []
    impact_targets: list[float] = []
    for risk in agent.risk_register.values():
        features = await build_risk_features(agent, risk)
        samples.append(
            [
                features.get("schedule_pressure", 0.0),
                features.get("cost_pressure", 0.0),
                features.get("quality_pressure", 0.0),
                features.get("resource_pressure", 0.0),
                features.get("risk_indicator", 0.0),
            ]
        )
        probability_targets.append(float(risk.get("probability", 3)))
        impact_targets.append(float(risk.get("impact", 3)))
    if len(samples) < 4:
        return
    try:
        from sklearn.ensemble import GradientBoostingRegressor

        agent._local_probability_model = GradientBoostingRegressor(random_state=42)
        agent._local_probability_model.fit(samples, probability_targets)
        agent._local_impact_model = GradientBoostingRegressor(random_state=42)
        agent._local_impact_model.fit(samples, impact_targets)
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ):
        agent._local_probability_model = None
        agent._local_impact_model = None


async def predict_risk_metrics(agent: RiskManagementAgent, risk: dict[str, Any]) -> dict[str, Any]:
    """Use ML to predict risk probability and impact."""
    features = await build_risk_features(agent, risk)
    if agent.ml_service:
        prediction = await agent.ml_service.predict_classification(features)
        if prediction.get("status") == "predicted":
            result = prediction.get("result", {}) or {}
            probability = result.get("probability") or result.get("likelihood")
            impact = result.get("impact")
            if probability or impact:
                return {
                    "probability": coerce_rating(probability, fallback=risk.get("probability", 3)),
                    "impact": coerce_rating(impact, fallback=risk.get("impact", 3)),
                    "severity_score": result.get("severity_score"),
                }
        if prediction.get("status") == "predicted_mock":
            mock_probability = features.get("risk_indicator", risk.get("probability", 3))
            mock_impact = features.get("impact_indicator", risk.get("impact", 3))
            return {
                "probability": coerce_rating(mock_probability, fallback=risk.get("probability", 3)),
                "impact": coerce_rating(mock_impact, fallback=risk.get("impact", 3)),
            }

    if agent._local_probability_model and agent._local_impact_model:
        try:
            model_features = [
                features.get("schedule_pressure", 0.0),
                features.get("cost_pressure", 0.0),
                features.get("quality_pressure", 0.0),
                features.get("resource_pressure", 0.0),
                features.get("risk_indicator", 0.0),
            ]
            probability_pred = float(agent._local_probability_model.predict([model_features])[0])
            impact_pred = float(agent._local_impact_model.predict([model_features])[0])
            return {
                "probability": coerce_rating(
                    round(probability_pred), fallback=risk.get("probability", 3)
                ),
                "impact": coerce_rating(round(impact_pred), fallback=risk.get("impact", 3)),
            }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ):
            pass

    history = agent.risk_histories.get(risk.get("risk_id"), [])
    if history:
        probabilities = [
            entry.get("probability", risk.get("probability", 3))
            for entry in history
            if entry.get("probability") is not None
        ]
        impacts = [
            entry.get("impact", risk.get("impact", 3))
            for entry in history
            if entry.get("impact") is not None
        ]
        probability = round(sum(probabilities) / len(probabilities)) if probabilities else None
        impact = round(sum(impacts) / len(impacts)) if impacts else None
    else:
        probability = None
        impact = None

    if probability is None or impact is None:
        category = risk.get("category")
        category_risks = [r for r in agent.risk_register.values() if r.get("category") == category]
        if category_risks:
            probability_values = [
                r.get("probability", 3) for r in category_risks if r.get("probability") is not None
            ]
            impact_values = [
                r.get("impact", 3) for r in category_risks if r.get("impact") is not None
            ]
            if probability is None and probability_values:
                probability = round(sum(probability_values) / len(probability_values))
            if impact is None and impact_values:
                impact = round(sum(impact_values) / len(impact_values))

    probability = probability or risk.get("probability", 3)
    impact = impact or risk.get("impact", 3)
    return {"probability": probability, "impact": impact}


async def calculate_quantitative_impact(
    agent: RiskManagementAgent, risk: dict[str, Any]
) -> dict[str, Any]:
    """Calculate quantitative impact on schedule and cost."""
    project_id = risk.get("project_id")
    schedule_distribution = await fetch_schedule_baseline(agent, project_id)
    financial_distribution = await fetch_financial_distribution(agent, project_id)
    baseline_duration = schedule_distribution.get("baseline_duration_days", 100.0)
    baseline_cost = financial_distribution.get("baseline_cost", 1_000_000.0)
    probability = min(1.0, max(0.0, (risk.get("probability", 3) / 5)))
    impact_factor = risk.get("impact", 3) / 5
    schedule_variance = schedule_distribution.get("mean_delay_days")
    if schedule_variance is None:
        schedule_variance = baseline_duration * 0.1
    cost_variance = financial_distribution.get("mean_cost_overrun")
    if cost_variance is None:
        cost_variance = baseline_cost * 0.05
    expected_schedule = probability * impact_factor * schedule_variance
    expected_cost = probability * impact_factor * cost_variance
    return {
        "schedule_impact_days": round(expected_schedule, 2),
        "cost_impact": round(expected_cost, 2),
        "baseline_duration_days": baseline_duration,
        "baseline_cost": baseline_cost,
        "probability": probability,
        "impact_factor": impact_factor,
    }


# ---------------------------------------------------------------------------
# Mitigation helpers
# ---------------------------------------------------------------------------


async def recommend_mitigation_strategies(
    agent: RiskManagementAgent, risk: dict[str, Any]
) -> list[str]:
    """Recommend mitigation strategies from knowledge base."""
    base_strategies = [
        "Regular monitoring and reviews",
        "Allocate contingency reserves",
        "Implement early warning system",
    ]
    if agent.knowledge_base_service:
        guidance = await agent.knowledge_base_service.query_mitigations(risk)
        guidance_strategies = [item["strategy"] for item in guidance if item.get("strategy")]
        if guidance_strategies:
            return list(dict.fromkeys(guidance_strategies + base_strategies))
    return base_strategies


async def calculate_residual_risk(risk: dict[str, Any], mitigation_plan: dict[str, Any]) -> float:
    """Calculate residual risk after mitigation."""
    original_score = risk.get("score", 0)
    reduction_factors = {"avoid": 0.9, "mitigate": 0.5, "transfer": 0.3, "accept": 0.0}
    reduction = reduction_factors.get(mitigation_plan.get("strategy", "accept"), 0.0)
    residual = original_score * (1 - reduction)
    return residual  # type: ignore


async def resolve_mitigation_owner(
    agent: RiskManagementAgent, risk: dict[str, Any], mitigation_data: dict[str, Any]
) -> str | None:
    if mitigation_data.get("responsible_person"):
        return mitigation_data.get("responsible_person")
    if agent.resource_management_service:
        for method in ("assign_owner", "get_available_owner", "resolve_owner"):
            if hasattr(agent.resource_management_service, method):
                try:
                    owner = await getattr(agent.resource_management_service, method)(risk)
                    if owner:
                        return owner
                except (
                    ConnectionError,
                    TimeoutError,
                    ValueError,
                    KeyError,
                    TypeError,
                    RuntimeError,
                    OSError,
                ):
                    continue
    return risk.get("owner")


async def create_mitigation_tasks(
    agent: RiskManagementAgent,
    risk: dict[str, Any],
    tasks: list[dict[str, Any]],
    owner: str | None,
) -> list[dict[str, Any]]:
    created: list[dict[str, Any]] = []
    if not tasks:
        return created
    for task in tasks:
        payload = {
            "title": task.get("title") or task.get("summary"),
            "description": task.get("description"),
            "priority": task.get("priority", "Medium"),
            "owner": task.get("owner") or owner,
            "due_date": task.get("due_date"),
            "labels": ["risk", risk.get("category", "risk")],
            "risk_id": risk.get("risk_id"),
            "project_id": risk.get("project_id"),
        }
        created.append({"status": "pending", **payload})

    for connector_type, service in agent.project_management_services.items():
        try:
            result = await service.create_tasks(risk.get("project_id"), created)
            for task, response in zip(created, result):
                task["status"] = response.get("status", "created")
                task["external_id"] = response.get("task_id") or response.get("id")
                task["system"] = connector_type
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ):
            continue

    return created


# ---------------------------------------------------------------------------
# Trigger helpers
# ---------------------------------------------------------------------------


async def check_risk_triggers(risk: dict[str, Any]) -> dict[str, Any]:
    """Check if risk triggers have been activated."""
    triggers = risk.get("triggers") or []
    for trigger in triggers:
        threshold = trigger.get("threshold")
        current_value = trigger.get("current_value")
        status = trigger.get("status")
        if status == "triggered":
            return {
                "triggered": True,
                "trigger": trigger,
                "new_score": min(25, risk.get("score", 0) + 2),
            }
        if threshold is not None and current_value is not None and current_value >= threshold:
            trigger["status"] = "triggered"
            return {
                "triggered": True,
                "trigger": trigger,
                "new_score": min(25, risk.get("score", 0) + 2),
            }
    return {"triggered": False, "trigger": None, "new_score": risk.get("score")}


async def update_risk_from_trigger(risk: dict[str, Any], trigger_status: dict[str, Any]) -> None:
    """Update risk probability/impact based on trigger."""
    risk["probability"] = min(5, risk.get("probability", 3) + 1)
    risk["score"] = risk["probability"] * risk.get("impact", 3)


async def register_triggers(
    agent: RiskManagementAgent, risk_id: str, triggers: list[dict[str, Any]]
) -> None:
    normalized = []
    for trigger in triggers:
        trigger_id = trigger.get("trigger_id") or f"TRG-{uuid.uuid4().hex[:8]}"
        trigger_record = {
            "trigger_id": trigger_id,
            "risk_id": risk_id,
            "type": trigger.get("type", "threshold"),
            "threshold": trigger.get("threshold"),
            "current_value": trigger.get("current_value"),
            "status": trigger.get("status", "monitoring"),
            "created_at": trigger.get("created_at") or datetime.now(timezone.utc).isoformat(),
        }
        normalized.append(trigger_record)
        agent.triggers[trigger_id] = trigger_record
        if agent.db_service:
            await agent.db_service.store("risk_trigger_definitions", trigger_id, trigger_record)
    if normalized:
        await store_risk_dataset(agent, "risk_trigger_definitions", normalized, domain="triggers")


# ---------------------------------------------------------------------------
# Monte Carlo helpers
# ---------------------------------------------------------------------------


async def perform_monte_carlo_simulation(
    project_id: str,
    risks: list[dict[str, Any]],
    iterations: int,
    schedule_distribution: dict[str, Any] | None = None,
    financial_distribution: dict[str, Any] | None = None,
) -> dict[str, list[float]]:
    """Perform Monte Carlo simulation."""
    if iterations <= 0:
        return {"schedule": [], "cost": []}

    schedule_distribution = schedule_distribution or {}
    financial_distribution = financial_distribution or {}
    baseline_schedule_days = float(schedule_distribution.get("baseline_duration_days", 100.0))
    baseline_cost = float(financial_distribution.get("baseline_cost", 1_000_000.0))
    numpy_spec = importlib.util.find_spec("numpy")
    if numpy_spec:
        import numpy as np

        probabilities = np.array(
            [min(1.0, max(0.0, (risk.get("probability", 3) / 5))) for risk in risks],
            dtype=float,
        )
        impact_levels = np.array([risk.get("impact", 3) for risk in risks], dtype=float)

        schedule_impact_days = impact_levels * (baseline_schedule_days * 0.1 / 5.0)
        cost_impact = impact_levels * (baseline_cost * 0.05 / 5.0)

        rng = np.random.default_rng()
        if risks:
            occurrences = rng.random((iterations, len(risks))) < probabilities
            schedule_adjustments = occurrences * schedule_impact_days
            cost_adjustments = occurrences * cost_impact
            schedule_results = baseline_schedule_days + schedule_adjustments.sum(axis=1)
            cost_results = baseline_cost + cost_adjustments.sum(axis=1)
        else:
            schedule_results = np.full(iterations, baseline_schedule_days, dtype=float)
            cost_results = np.full(iterations, baseline_cost, dtype=float)

        return {
            "schedule": schedule_results.tolist(),
            "cost": cost_results.tolist(),
        }

    schedule_results_list: list[float] = []
    cost_results_list: list[float] = []
    for _ in range(iterations):
        schedule = baseline_schedule_days
        cost = baseline_cost
        for risk in risks:
            probability = min(1.0, max(0.0, (risk.get("probability", 3) / 5)))
            impact = risk.get("impact", 3)
            if random.random() < probability:
                schedule += impact * (baseline_schedule_days * 0.1 / 5.0)
                cost += impact * (baseline_cost * 0.05 / 5.0)
        schedule_results_list.append(schedule)
        cost_results_list.append(cost)

    return {"schedule": schedule_results_list, "cost": cost_results_list}


async def calculate_percentile(data: list[float], percentile: int) -> float:
    """Calculate percentile value."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    index = int(len(sorted_data) * percentile / 100)
    return sorted_data[min(index, len(sorted_data) - 1)]


async def offload_or_simulate(
    agent: RiskManagementAgent,
    project_id: str,
    risks: list[dict[str, Any]],
    iterations: int,
    *,
    schedule_distribution: dict[str, Any],
    financial_distribution: dict[str, Any],
) -> dict[str, list[float]]:
    offload_result = await submit_simulation_job(
        agent,
        project_id,
        risks,
        iterations,
        schedule_distribution=schedule_distribution,
        financial_distribution=financial_distribution,
    )
    if offload_result:
        return offload_result
    return await perform_monte_carlo_simulation(
        project_id,
        risks,
        iterations,
        schedule_distribution=schedule_distribution,
        financial_distribution=financial_distribution,
    )


async def submit_simulation_job(
    agent: RiskManagementAgent,
    project_id: str,
    risks: list[dict[str, Any]],
    iterations: int,
    *,
    schedule_distribution: dict[str, Any],
    financial_distribution: dict[str, Any],
) -> dict[str, list[float]] | None:
    azure_batch_endpoint = agent.simulation_offload.get("azure_batch_endpoint")
    databricks_endpoint = agent.simulation_offload.get("databricks_endpoint")
    if not azure_batch_endpoint and not databricks_endpoint:
        return None
    payload = {
        "project_id": project_id,
        "iterations": iterations,
        "risks": risks,
        "schedule_distribution": schedule_distribution,
        "financial_distribution": financial_distribution,
    }
    endpoint = azure_batch_endpoint or databricks_endpoint
    response = await post_json(endpoint, payload) if endpoint else None
    if not response:
        return None
    results = response.get("results") if isinstance(response, dict) else None
    if isinstance(results, dict) and "schedule" in results and "cost" in results:
        return {
            "schedule": results.get("schedule", []),
            "cost": results.get("cost", []),
        }
    return None


# ---------------------------------------------------------------------------
# Data validation
# ---------------------------------------------------------------------------


async def validate_risk_record(
    agent: RiskManagementAgent, *, risk: dict[str, Any], tenant_id: str
) -> dict[str, Any]:
    impact_value = risk.get("impact")
    likelihood_value = risk.get("likelihood", risk.get("probability"))
    impact_map = {1: "low", 2: "low", 3: "medium", 4: "high", 5: "critical"}
    likelihood_map = {1: "rare", 2: "unlikely", 3: "possible", 4: "likely", 5: "likely"}
    mapped_impact = impact_map.get(impact_value, impact_value)
    mapped_likelihood = likelihood_map.get(likelihood_value, likelihood_value)
    record = {
        "id": risk.get("risk_id"),
        "tenant_id": tenant_id,
        "title": risk.get("title"),
        "description": risk.get("description"),
        "impact": mapped_impact or "medium",
        "likelihood": mapped_likelihood or "possible",
        "status": risk.get("status", "open"),
        "owner": risk.get("owner"),
        "classification": risk.get("classification", "internal"),
        "created_at": risk.get("created_at"),
    }
    if risk.get("last_updated"):
        record["updated_at"] = risk.get("last_updated")
    errors = validate_against_schema(agent.risk_schema_path, record)
    if errors:
        for error in errors:
            agent.logger.warning("Risk schema error %s: %s", error.path, error.message)
    report = evaluate_quality_rules("risk", record)
    issues = [issue.__dict__ for issue in report.issues]
    if issues:
        for issue in issues:
            agent.logger.warning(
                "Risk data quality issue %s: %s", issue["rule_id"], issue["message"]
            )
    return {"is_valid": len(errors) == 0 and report.is_valid, "issues": issues}


# ---------------------------------------------------------------------------
# NLP extraction helpers
# ---------------------------------------------------------------------------


async def extract_risks_from_documents(
    agent: RiskManagementAgent, documents: list[dict[str, Any] | str]
) -> list[dict[str, Any]]:
    """Extract potential risks from documents using NLP."""
    extracted: list[dict[str, Any]] = []
    if agent.risk_nlp_extractor:
        extracted.extend(agent.risk_nlp_extractor.extract_risks(documents))
    if agent.cognitive_search_service:
        extracted.extend(agent.cognitive_search_service.extract_risks(documents))
    return extracted


async def prime_risk_extractor(agent: RiskManagementAgent) -> None:
    training_documents = agent.config.get("risk_nlp_training_documents") if agent.config else None
    training_path = agent.config.get("risk_nlp_training_path") if agent.config else None
    documents: list[dict[str, Any] | str] = []

    if isinstance(training_documents, list):
        documents.extend(training_documents)

    if training_path:
        try:
            path = Path(training_path)
            if path.is_file():
                if path.suffix.lower() == ".json":
                    documents.extend(json.loads(path.read_text()))
                else:
                    documents.append(path.read_text())
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ):
            documents = documents

    if documents:
        await train_risk_extractor(agent, documents)


async def train_risk_extractor(
    agent: RiskManagementAgent, documents: list[dict[str, Any] | str]
) -> None:
    if agent.risk_nlp_extractor and hasattr(agent.risk_nlp_extractor, "train"):
        try:
            agent.risk_nlp_extractor.train(documents)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ):
            return


# ---------------------------------------------------------------------------
# Data lake / event bus / HTTP helpers
# ---------------------------------------------------------------------------


async def store_risk_dataset(
    agent: RiskManagementAgent,
    dataset_type: str,
    payload: list[dict[str, Any]],
    *,
    domain: str,
) -> dict[str, Any]:
    details: dict[str, Any] = {"dataset_type": dataset_type, "stored": False}
    if not payload:
        return details
    if agent.data_lake_manager:
        details["data_lake"] = agent.data_lake_manager.store_dataset(dataset_type, domain, payload)
    if agent.synapse_manager:
        details["synapse"] = {
            "workspace": agent.synapse_manager.workspace_name,
            "sql_pool": agent.synapse_manager.sql_pool_name,
            "spark_pool": agent.synapse_manager.spark_pool_name,
            "status": "queued",
        }
    details["stored"] = bool(details.get("data_lake") or details.get("synapse"))
    return details


async def publish_risk_event(
    agent: RiskManagementAgent, event_type: str, payload: dict[str, Any]
) -> None:
    event = {
        "event_type": event_type,
        "payload": payload,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    agent.risk_events.append(event)
    if agent.event_bus:
        await agent.event_bus.publish(event_type, payload)


async def post_json(endpoint: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    try:
        req = url_request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with url_request.urlopen(req, timeout=5) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ):
        return None


async def fetch_schedule_baseline(
    agent: RiskManagementAgent, project_id: str | None
) -> dict[str, Any]:
    if project_id and project_id in agent.latest_schedule_signals:
        return agent.latest_schedule_signals[project_id]
    if isinstance(agent.schedule_baseline_fixture, dict) and agent.schedule_baseline_fixture:
        return agent.schedule_baseline_fixture
    if not project_id or not agent.schedule_agent_endpoint:
        return {"baseline_duration_days": 100.0}
    payload = {"action": "get_schedule_baseline", "project_id": project_id}
    response = await post_json(agent.schedule_agent_endpoint, payload)
    if response:
        return response
    return {"baseline_duration_days": 100.0}


async def fetch_financial_distribution(
    agent: RiskManagementAgent, project_id: str | None
) -> dict[str, Any]:
    if project_id and project_id in agent.latest_financial_signals:
        return agent.latest_financial_signals[project_id]
    if (
        isinstance(agent.financial_distribution_fixture, dict)
        and agent.financial_distribution_fixture
    ):
        return agent.financial_distribution_fixture
    if not project_id or not agent.financial_agent_endpoint:
        return {"baseline_cost": 1_000_000.0}
    payload = {"action": "get_cost_distribution", "project_id": project_id}
    response = await post_json(agent.financial_agent_endpoint, payload)
    if response:
        return response
    return {"baseline_cost": 1_000_000.0}


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------


async def handle_schedule_baseline_event(
    agent: RiskManagementAgent, payload: dict[str, Any]
) -> None:
    project_id = payload.get("project_id")
    if not project_id:
        return
    agent.latest_schedule_signals[project_id] = payload


async def handle_schedule_delay_event(agent: RiskManagementAgent, payload: dict[str, Any]) -> None:
    project_id = payload.get("project_id")
    if not project_id:
        return
    agent.latest_schedule_signals[project_id] = payload


async def handle_financial_update_event(
    agent: RiskManagementAgent, payload: dict[str, Any]
) -> None:
    project_id = payload.get("project_id")
    if not project_id:
        return
    agent.latest_financial_signals[project_id] = payload


async def handle_cost_overrun_event(agent: RiskManagementAgent, payload: dict[str, Any]) -> None:
    await evaluate_event_trigger(agent, payload, trigger_type="cost_overrun")


async def handle_milestone_missed_event(
    agent: RiskManagementAgent, payload: dict[str, Any]
) -> None:
    await evaluate_event_trigger(agent, payload, trigger_type="schedule_delay")


async def handle_quality_event(agent: RiskManagementAgent, payload: dict[str, Any]) -> None:
    await evaluate_event_trigger(agent, payload, trigger_type="quality_defect_rate")


async def handle_resource_utilization_event(
    agent: RiskManagementAgent, payload: dict[str, Any]
) -> None:
    await evaluate_event_trigger(agent, payload, trigger_type="resource_utilization")


async def evaluate_event_trigger(
    agent: RiskManagementAgent, payload: dict[str, Any], *, trigger_type: str
) -> None:
    project_id = payload.get("project_id")
    if not project_id:
        return
    threshold_map = {
        "cost_overrun": agent.risk_trigger_thresholds.get("cost_overrun_pct", 0.1),
        "schedule_delay": agent.risk_trigger_thresholds.get("schedule_delay_days", 10),
        "quality_defect_rate": agent.risk_trigger_thresholds.get("quality_defect_rate", 0.05),
        "resource_utilization": agent.risk_trigger_thresholds.get("resource_utilization", 0.9),
    }
    value_map = {
        "cost_overrun": payload.get("overrun_pct")
        or payload.get("cost_overrun_pct")
        or payload.get("variance_pct"),
        "schedule_delay": payload.get("delay_days")
        or payload.get("slip_days")
        or payload.get("delay"),
        "quality_defect_rate": payload.get("defect_rate") or payload.get("quality_defect_rate"),
        "resource_utilization": payload.get("utilization") or payload.get("resource_utilization"),
    }
    threshold = threshold_map.get(trigger_type)
    current_value = value_map.get(trigger_type)
    if threshold is None or current_value is None:
        return
    if float(current_value) < float(threshold):
        return
    triggered = []
    for risk in agent.risk_register.values():
        if risk.get("project_id") != project_id:
            continue
        await update_risk_from_trigger(
            risk,
            {
                "triggered": True,
                "trigger": {
                    "type": trigger_type,
                    "threshold": threshold,
                    "current_value": current_value,
                    "status": "triggered",
                },
                "new_score": min(25, risk.get("score", 0) + 2),
            },
        )
        triggered.append(
            {
                "risk_id": risk.get("risk_id"),
                "project_id": project_id,
                "trigger_type": trigger_type,
                "threshold": threshold,
                "current_value": current_value,
                "new_score": risk.get("score"),
            }
        )
    if triggered:
        await store_risk_dataset(agent, "risk_triggers", triggered, domain="triggers")
        for item in triggered:
            await publish_risk_event(agent, "risk.triggered", item)


# ---------------------------------------------------------------------------
# External risk signals
# ---------------------------------------------------------------------------


async def collect_external_risk_signals(
    agent: RiskManagementAgent, project_id: str
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for connector_type, service in agent.project_management_services.items():
        try:
            tasks = await service.get_tasks(project_id, filters={"labels": ["risk"]}, limit=25)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ):
            tasks = []
        for task in tasks:
            signals.append(
                {
                    "source": connector_type,
                    "item_id": task.get("id") or task.get("key") or task.get("work_item_id"),
                    "summary": task.get("summary") or task.get("title") or task.get("name"),
                    "status": task.get("status"),
                    "risk_level": task.get("priority") or task.get("severity"),
                }
            )
    return signals


# ---------------------------------------------------------------------------
# Project management service initialization
# ---------------------------------------------------------------------------


def initialize_project_management_services(
    config: dict[str, Any] | None,
) -> dict[str, ProjectManagementService]:
    services: dict[str, ProjectManagementService] = {}
    if not config:
        return services
    connector_types = ["planview", "ms_project", "jira", "azure_devops"]
    for connector_type in connector_types:
        env_map = {
            "planview": "PLANVIEW_INSTANCE_URL",
            "ms_project": "MS_PROJECT_SITE_URL",
            "jira": "JIRA_INSTANCE_URL",
            "azure_devops": "AZURE_DEVOPS_ORG_URL",
        }
        if not (config.get("enable_all_pm_connectors") or os.getenv(env_map[connector_type])):
            continue
        services[connector_type] = ProjectManagementService({"connector_type": connector_type})
    return services


# ---------------------------------------------------------------------------
# Agent configuration helper
# ---------------------------------------------------------------------------


def apply_config(agent: RiskManagementAgent, config: dict[str, Any] | None) -> None:
    """Set all config-derived attributes on *agent* during ``__init__``."""
    from risk_models import RiskNLPExtractor

    _default_categories = [
        "technical",
        "schedule",
        "financial",
        "compliance",
        "external",
        "resource",
    ]
    _default_keywords = [
        "risk",
        "failure",
        "incident",
        "disruption",
        "regulatory change",
        "supplier",
    ]
    _default_thresholds = {
        "cost_overrun_pct": 0.1,
        "schedule_delay_days": 10,
        "quality_defect_rate": 0.05,
        "resource_utilization": 0.9,
    }

    def _cfg(key: str, default: Any = None) -> Any:
        return config.get(key, default) if config else default

    agent.risk_categories = _cfg("risk_categories", _default_categories)
    agent.enable_external_risk_research = _cfg("enable_external_risk_research", False)
    agent.risk_search_keywords = _cfg("risk_search_keywords", _default_keywords)
    agent.risk_search_result_limit = int(_cfg("risk_search_result_limit", 5))
    agent.probability_scale = _cfg("probability_scale", [1, 2, 3, 4, 5])
    agent.impact_scale = _cfg("impact_scale", [1, 2, 3, 4, 5])
    agent.high_risk_threshold = _cfg("high_risk_threshold", 15)
    agent.risk_schema_path = Path(_cfg("risk_schema_path", "data/schemas/risk.schema.json"))

    risk_store_path = Path(_cfg("risk_store_path", "data/risk_register.json"))
    agent.risk_store = TenantStateStore(risk_store_path)

    # Data stores (initialised to empty; populated during ``initialize()``)
    agent.risk_register = {}
    agent.mitigation_plans = {}
    agent.triggers = {}
    agent.risk_histories = {}
    agent.db_service = None
    agent.grc_service = None
    agent.document_service = None
    agent.documentation_service = None
    agent.ml_service = None
    agent.project_management_services = {}
    agent.cognitive_search_service = None
    agent.knowledge_base_service = None
    agent.resource_management_service = _cfg("resource_management_service")
    agent.data_lake_manager = None
    agent.synapse_manager = None
    agent.event_bus = None
    agent.risk_events = []
    agent.risk_trigger_thresholds = _cfg("risk_trigger_thresholds", _default_thresholds)

    agent.risk_nlp_extractor = _cfg("risk_nlp_extractor")
    if not agent.risk_nlp_extractor:
        agent.risk_nlp_extractor = RiskNLPExtractor(
            model_name=_cfg("risk_nlp_model_name", "bert-base-uncased"),
            pipeline_task=_cfg("risk_nlp_pipeline_task", "zero-shot-classification"),
            labels=_cfg("risk_nlp_labels"),
            threshold=float(_cfg("risk_nlp_threshold", 0.6)),
            max_sentences=int(_cfg("risk_nlp_max_sentences", 80)),
            training_keywords=(
                tuple(config.get("risk_nlp_training_keywords"))
                if config and config.get("risk_nlp_training_keywords")
                else None
            ),
        )

    agent.schedule_agent_endpoint = _cfg("schedule_agent_endpoint") or (
        _cfg("related_agent_endpoints", {}) or {}
    ).get("schedule")
    agent.financial_agent_endpoint = _cfg("financial_agent_endpoint") or (
        _cfg("related_agent_endpoints", {}) or {}
    ).get("financial")
    agent.schedule_baseline_fixture = _cfg("schedule_baseline_fixture", {})
    agent.financial_distribution_fixture = _cfg("financial_distribution_fixture", {})
    agent.simulation_offload = _cfg("simulation_offload", {})
    agent.latest_schedule_signals = {}
    agent.latest_financial_signals = {}
    agent._local_probability_model = None
    agent._local_impact_model = None
