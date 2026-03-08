"""Action handler for optimizing program schedules."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from program_utils import (
    build_initial_schedule,
    detect_resource_schedule_conflicts,
    extract_alignment_terms,
    normalize_objectives,
)

from program_actions.identify_synergies import _calculate_synergy_savings, analyze_synergies

if TYPE_CHECKING:
    from program_management_agent import ProgramManagementAgent


async def handle_optimize_program(
    agent: ProgramManagementAgent,
    program_id: str,
    *,
    objectives: dict[str, float] | None,
    constraints: dict[str, Any],
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Optimize program schedule using multi-objective optimisation."""
    agent.logger.info("Optimizing program schedule for: %s", program_id)

    program = agent.program_store.get(tenant_id, program_id)
    if not program:
        raise ValueError(f"Program not found: {program_id}")

    constituent_projects = program.get("constituent_projects", [])
    project_schedules = await agent._get_project_schedules(constituent_projects)
    resource_allocations = await agent._get_resource_allocations(constituent_projects)
    project_costs = await agent._estimate_project_costs(constituent_projects, tenant_id=tenant_id)
    project_risks = await agent._estimate_project_risks(constituent_projects, tenant_id=tenant_id)
    project_details = await agent._get_project_details(constituent_projects)
    strategic_objectives = program.get("strategic_objectives", [])

    base_schedule = build_initial_schedule(constituent_projects, project_schedules)
    dependencies = await agent._identify_dependencies(
        constituent_projects,
        schedules=project_schedules,
        resource_allocations=resource_allocations,
    )
    synergy_analysis = await analyze_synergies(agent, project_details)
    synergy_map = _build_synergy_map(synergy_analysis)
    alignment_scores = _calculate_alignment_scores(agent, project_details, strategic_objectives)
    alignment_score = (
        sum(alignment_scores.values()) / max(1, len(alignment_scores)) if alignment_scores else 0.0
    )
    synergy_savings = await _calculate_synergy_savings(
        synergy_analysis.get("shared_components", []),
        synergy_analysis.get("vendor_consolidation", []),
        synergy_analysis.get("infrastructure_synergies", []),
        project_costs,
    )

    target_objectives = objectives or agent.optimization_objectives
    normalized_objectives = normalize_objectives(target_objectives, agent.optimization_objectives)

    rng = random.Random(hash(program_id) % 10_000)
    best_schedule = base_schedule
    best_score, best_breakdown = _score_schedule_candidate(
        agent,
        base_schedule,
        base_schedule,
        resource_allocations,
        project_costs,
        project_risks,
        normalized_objectives,
        alignment_score,
        synergy_map,
    )

    optimization_method = constraints.get("optimization_method", "genetic_algorithm")
    iterations = constraints.get("iterations", 30)
    if optimization_method in {"mixed_integer", "mixed_integer_programming", "mip"}:
        best_schedule, best_score, best_breakdown = _optimize_schedule_mip(
            agent,
            base_schedule,
            dependencies,
            resource_allocations,
            project_costs,
            project_risks,
            normalized_objectives,
            alignment_score,
            synergy_map,
            max_shift_days=constraints.get("max_shift_days", 15),
        )
    elif optimization_method in {"genetic", "genetic_algorithm"}:
        best_schedule, best_score, best_breakdown = _optimize_schedule_genetic(
            agent,
            base_schedule,
            dependencies,
            resource_allocations,
            project_costs,
            project_risks,
            normalized_objectives,
            alignment_score,
            synergy_map,
            iterations=iterations,
            max_shift_days=constraints.get("max_shift_days", 15),
            rng=rng,
        )
    else:
        for _ in range(iterations):
            candidate = _mutate_schedule(
                base_schedule,
                dependencies,
                rng=rng,
                max_shift_days=constraints.get("max_shift_days", 15),
            )
            score, breakdown = _score_schedule_candidate(
                agent,
                candidate,
                base_schedule,
                resource_allocations,
                project_costs,
                project_risks,
                normalized_objectives,
                alignment_score,
                synergy_map,
            )
            if score > best_score:
                best_schedule = candidate
                best_score = score
                best_breakdown = breakdown

    optimized_schedule = {
        project_id: {
            "start": data["start"].isoformat(),
            "end": data["end"].isoformat(),
            "duration_days": data["duration_days"],
        }
        for project_id, data in best_schedule.items()
    }

    optimization = {
        "program_id": program_id,
        "optimized_schedule": optimized_schedule,
        "objective_score": round(best_score, 4),
        "objective_breakdown": best_breakdown,
        "algorithm": optimization_method,
        "constraints": constraints,
        "alignment_score": alignment_score,
        "alignment_scores": alignment_scores,
        "synergy_savings": synergy_savings,
        "synergy_analysis": synergy_analysis,
        "optimized_at": datetime.now(timezone.utc).isoformat(),
    }

    if agent.db_service:
        await agent.db_service.store("program_optimizations", program_id, optimization)
        await agent.db_service.store(
            "program_analytics",
            program_id,
            {
                "program_id": program_id,
                "optimization_score": best_score,
                "objectives": normalized_objectives,
            },
        )
        await agent.db_service.store(
            "program_optimization_models",
            program_id,
            {
                "program_id": program_id,
                "optimization_method": optimization_method,
                "objectives": normalized_objectives,
                "alignment_scores": alignment_scores,
                "synergy_map": {f"{k[0]}::{k[1]}": v for k, v in synergy_map.items()},
                "constraints": constraints,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    await agent.event_bus.publish(
        "program.optimized",
        {
            "program_id": program_id,
            "tenant_id": tenant_id,
            "optimization": optimization,
            "correlation_id": correlation_id,
        },
    )

    await agent._publish_program_status_update(
        program_id,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        status_type="optimization",
        payload={
            "optimization_score": best_score,
            "alignment_score": alignment_score,
            "synergy_savings": synergy_savings.get("total", 0.0),
        },
    )

    return optimization


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _calculate_alignment_scores(
    agent: ProgramManagementAgent,
    project_details: dict[str, Any],
    strategic_objectives: list[str],
) -> dict[str, float]:
    if not strategic_objectives:
        return {project_id: 0.7 for project_id in project_details}
    objective_terms = extract_alignment_terms(" ".join(str(obj) for obj in strategic_objectives))
    if not objective_terms:
        return {project_id: 0.7 for project_id in project_details}
    scores: dict[str, float] = {}
    for project_id, detail in project_details.items():
        project_text = " ".join(
            str(value)
            for value in [
                detail.get("name"),
                detail.get("description"),
                " ".join(detail.get("scope", []) or []),
                " ".join(detail.get("tags", []) or []),
            ]
            if value
        )
        project_terms = extract_alignment_terms(project_text)
        if not project_terms:
            scores[project_id] = 0.5
            continue
        overlap = len(project_terms & objective_terms)
        scores[project_id] = max(0.0, min(1.0, overlap / max(1, len(objective_terms))))
    return scores


def _build_synergy_map(synergy_analysis: dict[str, Any]) -> dict[tuple[str, str], float]:
    synergy_map: dict[tuple[str, str], float] = {}

    def _add_synergies(items: list[dict[str, Any]], weight: float) -> None:
        for item in items:
            projects = item.get("projects", [])
            if len(projects) != 2:
                continue
            pair = tuple(sorted(projects))
            synergy_map[pair] = synergy_map.get(pair, 0.0) + weight * float(
                item.get("similarity", 0.0)
            )

    _add_synergies(synergy_analysis.get("shared_components", []), 0.6)
    _add_synergies(synergy_analysis.get("vendor_consolidation", []), 0.25)
    _add_synergies(synergy_analysis.get("infrastructure_synergies", []), 0.15)

    return synergy_map


def _calculate_synergy_score(
    schedule: dict[str, dict[str, Any]], synergy_map: dict[tuple[str, str], float]
) -> float:
    if not synergy_map:
        return 0.0
    total_weight = sum(synergy_map.values())
    if total_weight <= 0:
        return 0.0
    realized = 0.0
    for (project_a, project_b), weight in synergy_map.items():
        data_a = schedule.get(project_a)
        data_b = schedule.get(project_b)
        if not data_a or not data_b:
            continue
        start_a = data_a["start"]
        end_a = data_a["end"]
        start_b = data_b["start"]
        end_b = data_b["end"]
        if start_a <= end_b and start_b <= end_a:
            realized += weight
            continue
        gap = min(abs((start_a - end_b).days), abs((start_b - end_a).days))
        if gap <= 14:
            realized += weight * 0.5
    return min(1.0, realized / total_weight)


def _mutate_schedule(
    base_schedule: dict[str, dict[str, Any]],
    dependencies: list[dict[str, Any]],
    *,
    rng: random.Random,
    max_shift_days: int,
) -> dict[str, dict[str, Any]]:
    candidate: dict[str, dict[str, Any]] = {}
    dependency_map: dict[str, list[str]] = {}
    for dep in dependencies:
        predecessor = dep.get("predecessor")
        successor = dep.get("successor")
        if predecessor and successor:
            dependency_map.setdefault(successor, []).append(predecessor)

    for project_id, data in base_schedule.items():
        shift = rng.randint(-max_shift_days, max_shift_days)
        start = data["start"] + timedelta(days=shift)
        duration = data.get("duration_days", 180)
        for predecessor in dependency_map.get(project_id, []):
            predecessor_end = base_schedule.get(predecessor, {}).get("end")
            if predecessor_end and start < predecessor_end:
                start = predecessor_end + timedelta(days=1)
        candidate[project_id] = {
            "start": start,
            "end": start + timedelta(days=duration),
            "duration_days": duration,
        }
    return candidate


def _optimize_schedule_genetic(
    agent: ProgramManagementAgent,
    base_schedule: dict[str, dict[str, Any]],
    dependencies: list[dict[str, Any]],
    resource_allocations: dict[str, Any],
    project_costs: dict[str, float],
    project_risks: dict[str, float],
    objectives: dict[str, float],
    alignment_score: float,
    synergy_map: dict[tuple[str, str], float],
    *,
    iterations: int,
    max_shift_days: int,
    rng: random.Random,
    population_size: int = 12,
) -> tuple[dict[str, dict[str, Any]], float, dict[str, float]]:
    population = [
        _mutate_schedule(base_schedule, dependencies, rng=rng, max_shift_days=max_shift_days)
        for _ in range(max(2, population_size))
    ]
    population.append(base_schedule)
    scored = [
        _score_schedule_candidate(
            agent,
            candidate,
            base_schedule,
            resource_allocations,
            project_costs,
            project_risks,
            objectives,
            alignment_score,
            synergy_map,
        )
        for candidate in population
    ]
    best_idx = max(range(len(population)), key=lambda idx: scored[idx][0])
    best_schedule = population[best_idx]
    best_score, best_breakdown = scored[best_idx]

    for _ in range(iterations):
        ranked = sorted(
            zip(population, scored),
            key=lambda item: item[1][0],
            reverse=True,
        )
        elites = [item[0] for item in ranked[: max(2, len(ranked) // 3)]]
        new_population = elites[:]
        while len(new_population) < population_size:
            parent_a, parent_b = rng.sample(elites, 2)
            child: dict[str, dict[str, Any]] = {}
            for project_id in base_schedule.keys():
                child[project_id] = (
                    parent_a.get(project_id) if rng.random() < 0.5 else parent_b.get(project_id)
                )  # type: ignore
            child = _mutate_schedule(child, dependencies, rng=rng, max_shift_days=max_shift_days)
            new_population.append(child)
        population = new_population
        scored = [
            _score_schedule_candidate(
                agent,
                candidate,
                base_schedule,
                resource_allocations,
                project_costs,
                project_risks,
                objectives,
                alignment_score,
                synergy_map,
            )
            for candidate in population
        ]
        best_idx = max(range(len(population)), key=lambda idx: scored[idx][0])
        candidate_score, candidate_breakdown = scored[best_idx]
        if candidate_score > best_score:
            best_schedule = population[best_idx]
            best_score = candidate_score
            best_breakdown = candidate_breakdown

    return best_schedule, best_score, best_breakdown


def _optimize_schedule_mip(
    agent: ProgramManagementAgent,
    base_schedule: dict[str, dict[str, Any]],
    dependencies: list[dict[str, Any]],
    resource_allocations: dict[str, Any],
    project_costs: dict[str, float],
    project_risks: dict[str, float],
    objectives: dict[str, float],
    alignment_score: float,
    synergy_map: dict[tuple[str, str], float],
    *,
    max_shift_days: int,
) -> tuple[dict[str, dict[str, Any]], float, dict[str, float]]:
    candidate = {key: value.copy() for key, value in base_schedule.items()}
    best_score, best_breakdown = _score_schedule_candidate(
        agent,
        candidate,
        base_schedule,
        resource_allocations,
        project_costs,
        project_risks,
        objectives,
        alignment_score,
        synergy_map,
    )
    improved = True
    shift_options = [-max_shift_days, 0, max_shift_days]
    while improved:
        improved = False
        for project_id, data in candidate.items():
            best_local = (best_score, data)
            for shift in shift_options:
                shifted = data.copy()
                shifted_start = shifted["start"] + timedelta(days=shift)
                shifted["start"] = shifted_start
                shifted["end"] = shifted_start + timedelta(days=shifted["duration_days"])
                test_schedule = candidate.copy()
                test_schedule[project_id] = shifted
                score, breakdown = _score_schedule_candidate(
                    agent,
                    test_schedule,
                    base_schedule,
                    resource_allocations,
                    project_costs,
                    project_risks,
                    objectives,
                    alignment_score,
                    synergy_map,
                )
                if score > best_local[0]:
                    best_local = (score, shifted)
                    best_breakdown = breakdown
            if best_local[0] > best_score:
                candidate[project_id] = best_local[1]
                best_score = best_local[0]
                improved = True
    return candidate, best_score, best_breakdown


def _score_schedule_candidate(
    agent: ProgramManagementAgent,
    candidate: dict[str, dict[str, Any]],
    baseline: dict[str, dict[str, Any]],
    resource_allocations: dict[str, Any],
    project_costs: dict[str, float],
    project_risks: dict[str, float],
    objectives: dict[str, float],
    alignment_score: float,
    synergy_map: dict[tuple[str, str], float],
) -> tuple[float, dict[str, float]]:
    delay_days = 0.0
    for project_id, data in candidate.items():
        baseline_start = baseline.get(project_id, {}).get("start")
        if baseline_start and data["start"] > baseline_start:
            delay_days += (data["start"] - baseline_start).days

    total_cost = sum(project_costs.values()) or 1.0
    max_cost = total_cost * 1.2
    avg_risk = sum(project_risks.values()) / max(1, len(project_risks))

    overlap_conflicts = detect_resource_schedule_conflicts(candidate, resource_allocations)
    conflict_penalty = min(1.0, overlap_conflicts / max(1, len(candidate)))

    schedule_score = max(0.0, 1 - delay_days / (max(1, len(candidate)) * 30))
    cost_score = max(0.0, 1 - total_cost / max_cost)
    risk_score = max(0.0, 1 - avg_risk)
    utilization_score = max(0.0, 1 - conflict_penalty)
    synergy_score = _calculate_synergy_score(candidate, synergy_map)

    breakdown = {
        "utilization": round(utilization_score, 4),
        "cost": round(cost_score, 4),
        "risk": round(risk_score, 4),
        "schedule": round(schedule_score, 4),
        "alignment": round(max(0.0, min(1.0, alignment_score)), 4),
        "synergy": round(synergy_score, 4),
    }
    overall = sum(breakdown[key] * objectives.get(key, 0.0) for key in breakdown)
    return overall, breakdown
