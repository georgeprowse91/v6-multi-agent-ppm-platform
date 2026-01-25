from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..store import Store, Entity
from ..utils import now_iso, json_dumps, new_id
from ..security import DEFAULT_CLASSIFICATION


# -----------------------------
# Helpers
# -----------------------------
def _artifact(store: Store, *, parent: Entity, name: str, content_md: str, actor: str) -> Entity:
    art = store.create_entity(
        type="artifact",
        title=name,
        status="Generated",
        classification=parent.classification,
        data={
            "parent_id": parent.id,
            "mime": "text/markdown",
            "content": content_md,
            "generated_by": actor,
        },
    )
    store.link(parent.id, art.id, "has_artifact")
    return art


def _ensure(store: Store, entity_id: str | None) -> Entity:
    if not entity_id:
        raise ValueError("entity_id is required for this agent action")
    ent = store.get_entity(entity_id, include_data=True)
    if not ent:
        raise KeyError(f"Entity not found: {entity_id}")
    return ent


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _score_to_band(score: float) -> str:
    if score >= 0.8:
        return "High"
    if score >= 0.55:
        return "Medium"
    return "Low"


# -----------------------------
# Agent 1: Intent Router
# -----------------------------
INTENT_KEYWORDS = [
    ("intake", ["intake", "request", "demand", "idea", "proposal"]),
    ("business_case", ["business case", "roi", "npv", "benefit", "investment"]),
    ("portfolio", ["portfolio", "priorit", "optim", "score", "funding"]),
    ("program", ["program", "benefit", "kpi", "dependency"]),
    ("project", ["project", "charter", "scope", "wbs"]),
    ("schedule", ["schedule", "plan", "timeline", "critical path", "baseline"]),
    ("resource", ["resource", "capacity", "allocation", "availability", "skills"]),
    ("financial", ["budget", "cost", "actual", "variance", "capex", "opex"]),
    ("vendor", ["vendor", "procurement", "contract", "supplier"]),
    ("quality", ["quality", "test", "acceptance", "gate", "defect"]),
    ("risk", ["risk", "issue", "mitigation"]),
    ("compliance", ["compliance", "policy", "audit", "gdpr", "soc", "iso", "pspf", "ism"]),
    ("change", ["change request", "cr", "scope change", "configuration"]),
    ("release", ["release", "deployment", "readiness"]),
    ("knowledge", ["knowledge", "lesson", "document", "runbook"]),
    ("improvement", ["process mining", "continuous improvement", "bottleneck"]),
    ("stakeholder", ["stakeholder", "communication", "comms", "update", "status report"]),
    ("analytics", ["analytics", "insight", "dashboard", "kpi", "report"]),
    ("sync", ["sync", "integration", "connector", "jira", "sap", "workday", "teams"]),
    ("workflow", ["workflow", "approval", "gate", "process"]),
    ("health", ["health", "monitoring", "observability", "uptime", "error"]),
]

DOMAIN_LABELS = {
    "intake": "Demand Management & Intake",
    "business_case": "Business Case & Investment Analysis",
    "portfolio": "Portfolio Strategy & Optimization",
    "program": "Program Management",
    "project": "Project Definition & Scope Management",
    "schedule": "Schedule & Planning",
    "resource": "Resource & Capacity Management",
    "financial": "Financial Management",
    "vendor": "Vendor & Procurement Management",
    "quality": "Quality Management",
    "risk": "Risk & Issue Management",
    "compliance": "Compliance & Regulatory Management",
    "change": "Change & Configuration Management",
    "release": "Release & Deployment Management",
    "knowledge": "Knowledge & Document Management",
    "improvement": "Continuous Improvement & Process Mining",
    "stakeholder": "Communications & Stakeholder Management",
    "analytics": "Analytics & Insights",
    "sync": "Data Synchronisation & Quality",
    "workflow": "Workflow & Process Engine",
    "health": "System Health & Monitoring",
}


def route_intent(query: str) -> Dict[str, Any]:
    q = (query or "").lower()
    hits: List[Tuple[str, float]] = []
    for intent, keys in INTENT_KEYWORDS:
        score = 0.0
        for k in keys:
            if k in q:
                score += 1.0
        if score > 0:
            # Normalise by number of keywords for that intent
            hits.append((intent, score / max(1.0, len(keys))))
    hits.sort(key=lambda x: x[1], reverse=True)
    if not hits:
        return {
            "intents": [],
            "route": "unknown",
            "confidence": 0.0,
            "suggestion": "Try mentioning a project, portfolio, risk, budget, schedule, or an integration name (Jira, SAP, Workday, Teams).",
        }
    top_intent, top_score = hits[0]
    return {
        "intents": [{"intent": i, "confidence": float(_clamp(s, 0.0, 1.0)), "label": DOMAIN_LABELS.get(i, i)} for i, s in hits[:5]],
        "route": top_intent,
        "confidence": float(_clamp(top_score, 0.0, 1.0)),
    }


# -----------------------------
# Agent 2: Response Orchestration (stub)
# -----------------------------
def orchestrate(store: Store, *, actor: str, query: str, focus_entity_id: str | None = None) -> Dict[str, Any]:
    routing = route_intent(query)
    intent = routing.get("route")
    outputs: Dict[str, Any] = {"routing": routing, "actions": []}

    # In the real system, this would call multiple agents; here we call one “best” agent based on intent.
    intent_to_agent = {
        "intake": 4,
        "business_case": 5,
        "portfolio": 6,
        "program": 7,
        "project": 8,
        "schedule": 10,
        "resource": 11,
        "financial": 12,
        "vendor": 13,
        "quality": 14,
        "risk": 15,
        "compliance": 16,
        "change": 17,
        "release": 18,
        "knowledge": 19,
        "improvement": 20,
        "stakeholder": 21,
        "analytics": 22,
        "sync": 23,
        "workflow": 24,
        "health": 25,
    }
    agent_id = intent_to_agent.get(intent)
    if not agent_id:
        outputs["actions"].append({"type": "message", "text": "No matching domain agent found for query."})
        return outputs

    outputs["actions"].append({"type": "run_agent", "agent_id": agent_id, "entity_id": focus_entity_id})
    return outputs


# -----------------------------
# Domain agents
# -----------------------------
def agent_4_demand_intake(store: Store, *, actor: str, entity_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    intake = _ensure(store, entity_id)
    data = dict(intake.data)

    # Methodology recommendation heuristic
    size = float(data.get("size_score", inputs.get("size_score", 0.5)) or 0.5)
    risk = float(data.get("risk_score", inputs.get("risk_score", 0.5)) or 0.5)
    complexity = float(data.get("complexity_score", inputs.get("complexity_score", 0.5)) or 0.5)

    # Simple heuristic reflecting PRD: size/complexity/risk -> method
    if size < 0.4 and complexity < 0.5:
        method = "Agile"
    elif risk > 0.7 or complexity > 0.75:
        method = "Hybrid"
    else:
        method = "Waterfall"

    # Classification + routing
    req_type = data.get("request_type") or "Strategic initiative" if "strateg" in (data.get("description","").lower()) else "Operational improvement"
    triage_band = _score_to_band(1.0 - abs(0.5 - (size + complexity + risk) / 3.0))

    data.update({
        "classified_at": now_iso(),
        "request_type": req_type,
        "methodology_recommendation": method,
        "triage_band": triage_band,
        "duplicate_candidates": [],  # real system would use embeddings; prototype uses manual linking
    })

    store.update_entity(entity_id, data=data, status=data.get("status", "Under Review"))
    store.log_event(actor=actor, event_type="intake_classified", entity_id=entity_id, details={"methodology": method, "triage": triage_band})

    artifact = _artifact(
        store,
        parent=intake,
        name="Intake Triage Summary.md",
        content_md=f"""# Intake Triage Summary

**Intake:** {intake.title}

- Request type: **{req_type}**
- Recommended methodology: **{method}**
- Triage band: **{triage_band}**

## Key observations
- Size score: {size:.2f}
- Complexity score: {complexity:.2f}
- Risk score: {risk:.2f}

## Next actions
- Submit for approval gate (PMO / Executive)
- If approved, generate business case and investment analysis
""",
        actor=actor,
    )

    return {
        "updated_entity": entity_id,
        "recommended_methodology": method,
        "artifact_id": artifact.id,
    }


def agent_5_business_case(store: Store, *, actor: str, entity_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    ent = _ensure(store, entity_id)
    data = dict(ent.data)

    # Cost/benefit estimates
    cost = float(inputs.get("estimated_cost", data.get("estimated_cost", 250000)) or 0)
    benefit = float(inputs.get("annual_benefit", data.get("annual_benefit", 150000)) or 0)
    years = int(inputs.get("benefit_years", data.get("benefit_years", 3)) or 3)
    discount = float(inputs.get("discount_rate", data.get("discount_rate", 0.08)) or 0.08)

    # Simple NPV / ROI
    npv = -cost
    for t in range(1, years + 1):
        npv += benefit / ((1 + discount) ** t)
    roi = (benefit * years - cost) / max(cost, 1.0)
    payback_years = cost / max(benefit, 1.0)

    data.update({
        "estimated_cost": cost,
        "annual_benefit": benefit,
        "benefit_years": years,
        "discount_rate": discount,
        "roi": roi,
        "npv": npv,
        "payback_years": payback_years,
        "generated_at": now_iso(),
    })

    store.update_entity(entity_id, data=data, status="Draft")
    store.log_event(actor=actor, event_type="business_case_generated", entity_id=entity_id, details={"roi": roi, "npv": npv})

    artifact = _artifact(
        store,
        parent=ent,
        name="Business Case.md",
        content_md=f"""# Business Case (Draft)

**Item:** {ent.title}

## Summary
- Estimated cost: **${cost:,.0f}**
- Annual benefit: **${benefit:,.0f}**
- Benefit duration: **{years} years**
- Discount rate: **{discount:.2%}**

## Investment metrics
- ROI: **{roi:.2%}**
- NPV: **${npv:,.0f}**
- Payback period: **{payback_years:.2f} years**

## Risks / assumptions (prototype)
- Risks: {data.get('risks','(add in data JSON)')}
- Assumptions: {data.get('assumptions','(add in data JSON)')}

## Recommendations
- If ROI and NPV meet portfolio thresholds, progress to portfolio scoring and funding approval.
""",
        actor=actor,
    )

    return {"updated_entity": entity_id, "roi": roi, "npv": npv, "artifact_id": artifact.id}


def agent_6_portfolio(store: Store, *, actor: str, entity_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    # Portfolio scoring/optimisation can be run on a portfolio entity, but also works globally if entity_id refers to a business case.
    ent = _ensure(store, entity_id)

    # Collect candidate initiatives (business cases)
    candidates = store.list_entities(type="business_case", limit=200)
    if not candidates and ent.type == "business_case":
        candidates = [ent]

    budget = float(inputs.get("budget_cap", 1000000))

    scored=[]
    for c in candidates:
        d=c.data or {}
        cost=float(d.get("estimated_cost", inputs.get("default_cost", 250000)) or 250000)
        roi=float(d.get("roi", 0.2) or 0.2)
        risk=float(d.get("risk_score", 0.5) or 0.5)
        align=float(d.get("strategic_alignment", 0.6) or 0.6)
        score=_clamp(0.45*_clamp(roi, -1, 3) + 0.35*align + 0.20*(1-risk), -1, 3)
        scored.append({"id":c.id,"title":c.title,"cost":cost,"score":score,"roi":roi,"risk":risk,"alignment":align})

    scored.sort(key=lambda x:x["score"], reverse=True)

    # Simple greedy selection under budget
    selected=[]
    spend=0.0
    for it in scored:
        if spend + it["cost"] <= budget:
            selected.append(it)
            spend += it["cost"]

    recommendation={
        "budget_cap": budget,
        "selected": selected,
        "spend": spend,
        "unfunded": [it for it in scored if it not in selected],
        "generated_at": now_iso(),
    }

    # Attach as artifact
    artifact=_artifact(
        store,
        parent=ent,
        name="Portfolio Recommendation.md",
        content_md=f"""# Portfolio Recommendation

**Budget cap:** ${budget:,.0f}

## Recommended set (greedy under budget)

""" + "\n".join([f"- **{s['title']}** — score {s['score']:.2f}, cost ${s['cost']:,.0f}, roi {s['roi']:.2%}" for s in selected]) +
        f"""

**Total spend:** ${spend:,.0f}

## Notes
- Prototype uses a simple greedy optimisation. A production system would support multi-objective optimisation, constraints (skills, dependencies), and scenario planning.
""",
        actor=actor,
    )

    store.log_event(actor=actor, event_type="portfolio_optimised", entity_id=entity_id, details={"budget": budget, "selected_count": len(selected)})

    return {"recommendation": recommendation, "artifact_id": artifact.id}


def agent_7_program(store: Store, *, actor: str, entity_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    ent=_ensure(store, entity_id)

    program_title = inputs.get("program_title") or f"Program for {ent.title}"
    program = store.create_entity(
        type="program",
        title=program_title,
        status="Draft",
        classification=ent.classification,
        data={
            "vision": inputs.get("vision", "(add vision)") ,
            "objectives": inputs.get("objectives", ["Deliver benefits", "Coordinate dependencies"]) ,
            "kpis": inputs.get("kpis", {"benefit_realisation": "Pending", "on_time_pct": 85}),
            "created_from": ent.id,
        }
    )
    store.link(program.id, ent.id, "created_from")
    store.log_event(actor=actor, event_type="program_created", entity_id=program.id, details={"source": ent.id})

    artifact=_artifact(
        store,
        parent=program,
        name="Program Definition.md",
        content_md=f"""# Program Definition

**Program:** {program.title}

## Vision
{program.data.get('vision')}

## Objectives
""" + "\n".join([f"- {o}" for o in program.data.get('objectives',[])]) +
        "\n\n## KPIs\n" + "\n".join([f"- {k}: {v}" for k,v in (program.data.get('kpis') or {}).items()]) + "\n",
        actor=actor,
    )

    return {"program_id": program.id, "artifact_id": artifact.id}


def agent_8_project_definition(store: Store, *, actor: str, entity_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    ent=_ensure(store, entity_id)

    # If entity is intake/business_case, create a project. If entity is already project, enrich it.
    if ent.type != "project":
        proj = store.create_entity(
            type="project",
            title=inputs.get("project_title") or f"Project: {ent.title}",
            status="Initiating",
            classification=ent.classification,
            data={
                "methodology": inputs.get("methodology") or ent.data.get("methodology_recommendation") or "Hybrid",
                "objectives": inputs.get("objectives") or ["(add objective)"] ,
                "scope": inputs.get("scope") or ent.data.get("scope") or "(add scope)",
                "assumptions": ent.data.get("assumptions") or [],
                "constraints": ent.data.get("constraints") or [],
                "stakeholders": ent.data.get("stakeholders") or [],
                "source_entity": ent.id,
            },
        )
        store.link(ent.id, proj.id, "creates_project")
        ent_for_art = proj
    else:
        proj = ent
        ent_for_art = ent

    # Generate WBS (very simple: objectives -> work packages)
    objectives = proj.data.get("objectives") or ["(add objective)"]
    wbs_ids=[]
    for i,obj in enumerate(objectives, start=1):
        wbs = store.create_entity(
            type="wbs_item",
            title=f"{i}. {obj}",
            status="Planned",
            classification=proj.classification,
            data={"project_id": proj.id, "description": obj, "estimate_hours": int(inputs.get("default_wbs_hours", 80))},
        )
        store.link(proj.id, wbs.id, "has_wbs")
        wbs_ids.append(wbs.id)

    charter_md=f"""# Project Charter (Draft)

**Project:** {proj.title}

## Objectives
""" + "\n".join([f"- {o}" for o in objectives]) + f"""

## Scope
{proj.data.get('scope')}

## Assumptions
""" + "\n".join([f"- {a}" for a in (proj.data.get('assumptions') or [])]) + f"""

## Constraints
""" + "\n".join([f"- {c}" for c in (proj.data.get('constraints') or [])]) + "\n"

    artifact=_artifact(store, parent=ent_for_art, name="Project Charter.md", content_md=charter_md, actor=actor)

    store.log_event(actor=actor, event_type="project_charter_generated", entity_id=proj.id, details={"wbs_items": len(wbs_ids)})

    return {"project_id": proj.id, "wbs_item_ids": wbs_ids, "artifact_id": artifact.id}


def agent_9_governance(store: Store, *, actor: str, entity_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    proj=_ensure(store, entity_id)
    if proj.type != "project":
        raise ValueError("Agent 9 expects a project entity")

    gates = inputs.get("stage_gates") or [
        {"name": "Initiation", "status": "Pending"},
        {"name": "Planning", "status": "Pending"},
        {"name": "Execution", "status": "Pending"},
        {"name": "Closure", "status": "Pending"},
    ]
    data=dict(proj.data)
    data["governance"]={
        "stage_gates": gates,
        "reporting_cadence": inputs.get("reporting_cadence", "Weekly"),
        "configured_at": now_iso(),
    }
    store.update_entity(proj.id, data=data)
    store.log_event(actor=actor, event_type="governance_configured", entity_id=proj.id, details={"gates": len(gates)})

    artifact=_artifact(
        store,
        parent=proj,
        name="Governance Plan.md",
        content_md=f"""# Governance Plan

**Project:** {proj.title}

## Stage gates
""" + "\n".join([f"- {g['name']}: {g['status']}" for g in gates]) + f"""

## Reporting cadence
- {data['governance']['reporting_cadence']}

## Notes
- Prototype models gate structure only. Production system would implement automated evidence collection and approvals.
""",
        actor=actor,
    )

    return {"project_id": proj.id, "artifact_id": artifact.id}


def agent_10_schedule(store: Store, *, actor: str, entity_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    proj=_ensure(store, entity_id)
    if proj.type != "project":
        raise ValueError("Agent 10 expects a project entity")

    # Build tasks from WBS items
    wbs_links=[l for l in store.list_links(proj.id) if l["relation_type"]=="has_wbs" and l["from_id"]==proj.id]
    tasks=[]
    base_days=int(inputs.get("default_task_days", 10))
    for idx,l in enumerate(wbs_links, start=1):
        wbs=store.get_entity(l["to_id"], include_data=True)
        if not wbs:
            continue
        task=store.create_entity(
            type="schedule_task",
            title=f"Task {idx}: {wbs.title}",
            status="Planned",
            classification=proj.classification,
            data={
                "project_id": proj.id,
                "duration_days": base_days,
                "depends_on": [],
                "wbs_item_id": wbs.id,
            },
        )
        store.link(proj.id, task.id, "has_task")
        tasks.append(task)

    # Simple baseline dates (sequential)
    start_day=0
    for t in tasks:
        d=dict(t.data)
        d["baseline_start_day"]=start_day
        d["baseline_end_day"]=start_day + int(d.get("duration_days", base_days))
        start_day = d["baseline_end_day"]
        store.update_entity(t.id, data=d)

    data=dict(proj.data)
    data["schedule"]={
        "baseline_total_days": start_day,
        "baselined_at": now_iso(),
        "task_count": len(tasks),
    }
    store.update_entity(proj.id, data=data)
    store.log_event(actor=actor, event_type="schedule_baselined", entity_id=proj.id, details={"tasks": len(tasks), "days": start_day})

    artifact=_artifact(
        store,
        parent=proj,
        name="Schedule Baseline.md",
        content_md=f"""# Schedule Baseline

**Project:** {proj.title}

- Task count: **{len(tasks)}**
- Baseline duration: **{start_day} days**

## Tasks
""" + "\n".join([f"- {t.title} (days: {t.data.get('duration_days', base_days)})" for t in tasks]) + "\n",
        actor=actor,
    )

    return {"project_id": proj.id, "task_ids": [t.id for t in tasks], "artifact_id": artifact.id}


def agent_11_resources(store: Store, *, actor: str, entity_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    proj=_ensure(store, entity_id)
    if proj.type != "project":
        raise ValueError("Agent 11 expects a project entity")

    resources = store.list_entities(type="resource", limit=200)
    tasks_links=[l for l in store.list_links(proj.id) if l["relation_type"]=="has_task" and l["from_id"]==proj.id]
    tasks=[store.get_entity(l["to_id"], include_data=True) for l in tasks_links]
    tasks=[t for t in tasks if t]

    allocations=[]
    if resources and tasks:
        for t in tasks:
            r = random.choice(resources)
            d=dict(t.data)
            d["assigned_resource_id"]=r.id
            store.update_entity(t.id, data=d)
            allocations.append({"task": t.id, "resource": r.id})

    # Simple over-allocation check (counts tasks per resource)
    per_res={}
    for a in allocations:
        per_res[a["resource"]]=per_res.get(a["resource"],0)+1
    conflicts=[{"resource": rid, "task_count": n} for rid,n in per_res.items() if n>3]

    store.log_event(actor=actor, event_type="resources_planned", entity_id=proj.id, details={"allocations": len(allocations), "conflicts": len(conflicts)})

    artifact=_artifact(
        store,
        parent=proj,
        name="Resource & Capacity Plan.md",
        content_md=f"""# Resource & Capacity Plan (Prototype)

**Project:** {proj.title}

## Allocations
""" + "\n".join([f"- Task {a['task']} → Resource {a['resource']}" for a in allocations]) +
        ("\n\n## Potential conflicts\n" + "\n".join([f"- Resource {c['resource']} has {c['task_count']} tasks" for c in conflicts]) if conflicts else "\n\nNo conflicts detected by prototype rules."),
        actor=actor,
    )

    return {"project_id": proj.id, "allocations": allocations, "conflicts": conflicts, "artifact_id": artifact.id}


def agent_12_financial(store: Store, *, actor: str, entity_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    proj=_ensure(store, entity_id)
    if proj.type != "project":
        raise ValueError("Agent 12 expects a project entity")

    data=dict(proj.data)
    budget=float(inputs.get("budget", data.get("budget", 500000)) or 0)
    actual=float(inputs.get("actual_to_date", data.get("actual_to_date", budget*0.2)) or 0)
    variance=actual - budget

    data.update({"budget": budget, "actual_to_date": actual, "variance": variance, "currency": inputs.get("currency","USD")})
    store.update_entity(proj.id, data=data)
    store.log_event(actor=actor, event_type="financials_updated", entity_id=proj.id, details={"budget": budget, "actual": actual})

    artifact=_artifact(
        store,
        parent=proj,
        name="Financial Baseline & Variance.md",
        content_md=f"""# Financial Baseline & Variance

**Project:** {proj.title}

- Budget baseline: **{data['currency']} {budget:,.0f}**
- Actual to date: **{data['currency']} {actual:,.0f}**
- Variance: **{data['currency']} {variance:,.0f}**

## Notes
- Prototype does not connect to ERP; see Integrations page for simulated connectors.
""",
        actor=actor,
    )

    return {"project_id": proj.id, "budget": budget, "actual_to_date": actual, "variance": variance, "artifact_id": artifact.id}


def agent_13_vendor(store: Store, *, actor: str, entity_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    proj=_ensure(store, entity_id)

    vendor = store.create_entity(
        type="vendor",
        title=inputs.get("vendor_name", "Example Vendor"),
        status="Active",
        classification=proj.classification,
        data={"category": inputs.get("category","Software"), "risk_rating": inputs.get("risk_rating","Medium"), "contact": inputs.get("contact","vendor@example.com")},
    )
    store.link(proj.id, vendor.id, "uses_vendor")

    contract = store.create_entity(
        type="contract",
        title=f"Contract with {vendor.title}",
        status="Draft",
        classification=proj.classification,
        data={"vendor_id": vendor.id, "project_id": proj.id, "value": float(inputs.get("contract_value", 100000))},
    )
    store.link(vendor.id, contract.id, "has_contract")
    store.link(proj.id, contract.id, "has_contract")

    store.log_event(actor=actor, event_type="vendor_contract_created", entity_id=proj.id, details={"vendor": vendor.id, "contract": contract.id})

    artifact=_artifact(
        store,
        parent=contract,
        name="Procurement Summary.md",
        content_md=f"""# Vendor / Procurement Summary

**Project:** {proj.title}

- Vendor: **{vendor.title}**
- Category: {vendor.data.get('category')}
- Risk rating: {vendor.data.get('risk_rating')}

## Contract
- Value: ${contract.data.get('value'):,.0f}
- Status: {contract.status}

## Notes
- Prototype models vendor and contract records only.
""",
        actor=actor,
    )

    return {"vendor_id": vendor.id, "contract_id": contract.id, "artifact_id": artifact.id}


def agent_14_quality(store: Store, *, actor: str, entity_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    proj=_ensure(store, entity_id)
    if proj.type != "project":
        raise ValueError("Agent 14 expects a project entity")

    gates=inputs.get("quality_gates") or [
        {"name": "Requirements Complete", "status": "Pending"},
        {"name": "Test Plan Approved", "status": "Pending"},
        {"name": "UAT Passed", "status": "Pending"},
    ]

    q = store.create_entity(
        type="quality_plan",
        title=f"Quality Plan: {proj.title}",
        status="Draft",
        classification=proj.classification,
        data={"project_id": proj.id, "gates": gates, "metrics": {"defect_escape_rate": "Pending", "test_coverage": "Pending"}},
    )
    store.link(proj.id, q.id, "has_quality_plan")

    store.log_event(actor=actor, event_type="quality_plan_created", entity_id=proj.id, details={"quality_plan": q.id})

    artifact=_artifact(
        store,
        parent=q,
        name="Quality Plan.md",
        content_md=f"""# Quality Plan

**Project:** {proj.title}

## Quality gates
""" + "\n".join([f"- {g['name']}: {g['status']}" for g in gates]) + "\n",
        actor=actor,
    )

    return {"quality_plan_id": q.id, "artifact_id": artifact.id}


def agent_15_risk(store: Store, *, actor: str, entity_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    proj=_ensure(store, entity_id)

    risks=[]
    for r in inputs.get("risks", [
        {"title": "Schedule slippage", "probability": 0.4, "impact": 0.6, "mitigation": "Improve estimation; add buffer"},
        {"title": "Resource constraints", "probability": 0.5, "impact": 0.7, "mitigation": "Cross-train; adjust priorities"},
    ]):
        exposure=float(r.get("probability",0.5))*float(r.get("impact",0.5))
        risk_ent=store.create_entity(
            type="risk",
            title=r["title"],
            status="Open",
            classification=proj.classification,
            data={"project_id": proj.id, "probability": r.get("probability"), "impact": r.get("impact"), "exposure": exposure, "mitigation": r.get("mitigation")},
        )
        store.link(proj.id, risk_ent.id, "has_risk")
        risks.append(risk_ent)

    store.log_event(actor=actor, event_type="risk_register_created", entity_id=proj.id, details={"count": len(risks)})

    artifact=_artifact(
        store,
        parent=proj,
        name="Risk Register.md",
        content_md=f"""# Risk Register

**Project:** {proj.title}

""" + "\n".join([f"- **{r.title}** (exposure {r.data.get('exposure'):.2f}) — {r.data.get('mitigation')}" for r in risks]) + "\n",
        actor=actor,
    )

    return {"risk_ids": [r.id for r in risks], "artifact_id": artifact.id}


def agent_16_compliance(store: Store, *, actor: str, entity_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    proj=_ensure(store, entity_id)

    policies = store.list_entities(type="policy", limit=200)
    mapped=[]
    for p in policies:
        m=store.create_entity(
            type="compliance_check",
            title=f"Compliance: {p.title} for {proj.title}",
            status="Planned",
            classification=proj.classification,
            data={"project_id": proj.id, "policy_id": p.id, "status": "Planned", "evidence": "Pending"},
        )
        store.link(proj.id, m.id, "has_compliance_check")
        store.link(p.id, m.id, "policy_check")
        mapped.append(m)

    data=dict(proj.data)
    # Apply data classification suggestion
    data.setdefault("data_classification", proj.classification)
    store.update_entity(proj.id, data=data)

    store.log_event(actor=actor, event_type="compliance_mapped", entity_id=proj.id, details={"checks": len(mapped)})

    artifact=_artifact(
        store,
        parent=proj,
        name="Compliance Mapping.md",
        content_md=f"""# Compliance Mapping

**Project:** {proj.title}

- Data classification: **{data.get('data_classification')}**

## Policy checks (planned)
""" + "\n".join([f"- {m.title}" for m in mapped]) + "\n",
        actor=actor,
    )

    return {"compliance_check_ids": [m.id for m in mapped], "artifact_id": artifact.id}


def agent_17_change(store: Store, *, actor: str, entity_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    cr=_ensure(store, entity_id)
    data=dict(cr.data)

    # Impact analysis baseline
    impact = {
        "scope": data.get("impact_scope") or inputs.get("impact_scope") or "Medium",
        "schedule_days": float(data.get("impact_schedule_days") or inputs.get("impact_schedule_days") or 10),
        "cost": float(data.get("impact_cost") or inputs.get("impact_cost") or 25000),
        "resources": data.get("impact_resources") or inputs.get("impact_resources") or "Needs review",
    }

    data["impact"] = impact
    data["analysed_at"] = now_iso()
    store.update_entity(cr.id, data=data)
    store.log_event(actor=actor, event_type="change_impact_analysed", entity_id=cr.id, details=impact)

    artifact=_artifact(
        store,
        parent=cr,
        name="Change Impact Analysis.md",
        content_md=f"""# Change Impact Analysis

**Change:** {cr.title}

- Scope impact: **{impact['scope']}**
- Schedule impact: **{impact['schedule_days']} days**
- Cost impact: **${impact['cost']:,.0f}**
- Resource impact: {impact['resources']}

## Recommendation
- Submit to change control approval gate.
""",
        actor=actor,
    )

    return {"change_request_id": cr.id, "impact": impact, "artifact_id": artifact.id}


def agent_18_release(store: Store, *, actor: str, entity_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    rel=_ensure(store, entity_id)
    data=dict(rel.data)

    checks = {
        "quality_gates_passed": bool(inputs.get("quality_gates_passed", False)),
        "security_review_passed": bool(inputs.get("security_review_passed", False)),
        "compliance_ok": bool(inputs.get("compliance_ok", False)),
        "rollback_plan": bool(inputs.get("rollback_plan", True)),
    }
    readiness = all(checks.values())
    data["readiness_checks"] = checks
    data["readiness"] = "Ready" if readiness else "Not Ready"
    store.update_entity(rel.id, data=data)
    store.log_event(actor=actor, event_type="release_readiness_checked", entity_id=rel.id, details={"readiness": data["readiness"], **checks})

    artifact=_artifact(
        store,
        parent=rel,
        name="Release Readiness.md",
        content_md=f"""# Release Readiness

**Release:** {rel.title}

## Checks
""" + "\n".join([f"- {k.replace('_',' ')}: {'✅' if v else '❌'}" for k,v in checks.items()]) + f"""

## Overall
**{data['readiness']}**
""",
        actor=actor,
    )

    return {"release_id": rel.id, "readiness": data["readiness"], "artifact_id": artifact.id}


def agent_19_knowledge(store: Store, *, actor: str, entity_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    kb=_ensure(store, entity_id)
    data=dict(kb.data)
    data.setdefault("tags", inputs.get("tags", ["lessons", "ppm"]))
    data.setdefault("created_at", now_iso())
    store.update_entity(kb.id, data=data)
    store.log_event(actor=actor, event_type="knowledge_updated", entity_id=kb.id, details={"tags": data.get("tags")})

    return {"knowledge_id": kb.id, "tags": data.get("tags")}


def agent_20_improvement(store: Store, *, actor: str, entity_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    ent=_ensure(store, entity_id)

    # Process mining stub: infer bottlenecks from event log counts
    events = store.list_events(limit=500)
    counts = {}
    for e in events:
        counts[e["event_type"]] = counts.get(e["event_type"], 0) + 1

    top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:8]
    suggestions = [
        "Automate evidence collection for stage gates.",
        "Add SLA monitoring on approvals.",
        "Increase duplicate detection accuracy with embeddings.",
    ]

    store.log_event(actor=actor, event_type="process_mining_run", entity_id=ent.id, details={"events": len(events)})

    artifact=_artifact(
        store,
        parent=ent,
        name="Continuous Improvement Insights.md",
        content_md="# Continuous Improvement Insights\n\n## Top event types\n" + "\n".join([f"- {k}: {v}" for k,v in top]) + "\n\n## Suggested improvements\n" + "\n".join([f"- {s}" for s in suggestions]) + "\n",
        actor=actor,
    )

    return {"entity_id": ent.id, "top_events": top, "artifact_id": artifact.id}


def agent_21_stakeholder(store: Store, *, actor: str, entity_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    proj=_ensure(store, entity_id)

    stakeholders = inputs.get("stakeholders") or [
        {"name": "Executive Sponsor", "role": "Sponsor", "influence": "High", "interest": "High", "pref": "Email"},
        {"name": "PMO", "role": "Governance", "influence": "Medium", "interest": "High", "pref": "Teams"},
    ]
    created=[]
    for s in stakeholders:
        st = store.create_entity(
            type="stakeholder",
            title=s["name"],
            status="Active",
            classification=proj.classification,
            data={"project_id": proj.id, **s},
        )
        store.link(proj.id, st.id, "has_stakeholder")
        created.append(st)

    comm_plan = store.create_entity(
        type="communication_plan",
        title=f"Comms Plan: {proj.title}",
        status="Draft",
        classification=proj.classification,
        data={"project_id": proj.id, "cadence": inputs.get("cadence","Weekly"), "channels": ["Email", "Teams"], "audiences": [c.title for c in created]},
    )
    store.link(proj.id, comm_plan.id, "has_comms")

    store.log_event(actor=actor, event_type="stakeholders_configured", entity_id=proj.id, details={"stakeholders": len(created)})

    artifact=_artifact(
        store,
        parent=comm_plan,
        name="Stakeholder & Comms Plan.md",
        content_md=f"""# Stakeholder & Communications Plan

**Project:** {proj.title}

## Stakeholders
""" + "\n".join([f"- {s.title} ({s.data.get('role')}) – pref: {s.data.get('pref')}" for s in created]) + f"""

## Cadence
- {comm_plan.data.get('cadence')}

## Channels
""" + "\n".join([f"- {c}" for c in comm_plan.data.get('channels',[])]) + "\n",
        actor=actor,
    )

    return {"stakeholder_ids": [s.id for s in created], "comms_plan_id": comm_plan.id, "artifact_id": artifact.id}


def agent_22_analytics(store: Store, *, actor: str, entity_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    ent=_ensure(store, entity_id)

    # Basic KPIs across projects
    projects = store.list_entities(type="project", limit=200)
    kpis={
        "projects": len(projects),
        "active_projects": sum(1 for p in projects if p.status.lower() not in {"closed","cancelled"}),
        "avg_budget": (sum(float(p.data.get("budget",0) or 0) for p in projects)/len(projects)) if projects else 0,
        "risk_count": len(store.list_entities(type="risk", limit=500)),
        "open_change_requests": sum(1 for c in store.list_entities(type="change_request", limit=500) if c.status.lower() not in {"rejected","done","closed"}),
    }

    report=_artifact(
        store,
        parent=ent,
        name="Analytics Snapshot.md",
        content_md="# Analytics Snapshot\n\n" + "\n".join([f"- {k}: {v}" for k,v in kpis.items()]) + "\n",
        actor=actor,
    )

    store.log_event(actor=actor, event_type="analytics_generated", entity_id=ent.id, details=kpis)
    return {"kpis": kpis, "artifact_id": report.id}


def agent_23_data_sync(store: Store, *, actor: str, entity_id: str | None, inputs: Dict[str, Any]) -> Dict[str, Any]:
    # Simulate a connector sync by writing last_sync + metrics
    connectors = store.list_connectors()
    synced=[]
    for c in connectors:
        if inputs.get("only") and c["system_name"] not in inputs["only"]:
            continue
        c_id=c["id"]
        cfg=c.get("config") or {}
        status=c.get("status","Planned")
        last=now_iso()
        store.upsert_connector(connector_id=c_id, system_name=c["system_name"], category=c.get("category"), status=status, config=cfg, last_sync=last)
        synced.append({"system": c["system_name"], "last_sync": last})

    store.add_metric("connector_sync_count", float(len(synced)))
    store.log_event(actor=actor, event_type="connectors_synced", entity_id=entity_id, details={"count": len(synced)})

    return {"synced": synced}


def agent_24_workflow_engine(store: Store, *, actor: str, entity_id: str | None, inputs: Dict[str, Any]) -> Dict[str, Any]:
    # Prototype action: list workflow defs and optionally activate/deactivate (stored in DB).
    defs = store.list_workflow_defs()
    store.log_event(actor=actor, event_type="workflow_engine_inspected", entity_id=entity_id, details={"defs": len(defs)})
    return {"workflow_defs": [{"id": d["id"], "name": d["name"], "version": d["version"], "entity_type": d["entity_type"], "active": bool(d["active"])} for d in defs]}


def agent_25_system_health(store: Store, *, actor: str, entity_id: str | None, inputs: Dict[str, Any]) -> Dict[str, Any]:
    # System health is derived from basic metrics + recent events
    events = store.list_events(limit=100)
    metrics = store.latest_metrics(limit=50)

    # Simulated checks
    checks = {
        "db_reachable": True,
        "workflow_templates_loaded": len(store.list_workflow_defs()) > 0,
        "connectors_configured": len(store.list_connectors()) > 0,
        "recent_events": len(events),
    }
    status = "Healthy" if checks["db_reachable"] and checks["workflow_templates_loaded"] else "Degraded"

    store.add_metric("system_health", 1.0 if status == "Healthy" else 0.0)
    store.log_event(actor=actor, event_type="system_health_checked", entity_id=entity_id, details={"status": status})

    return {"status": status, "checks": checks, "metrics": metrics[:15], "recent_events": events[:15]}


# Baseline agents (1-3 and others not explicitly modelled as domain actions)
def agent_passthrough(store: Store, *, actor: str, entity_id: str | None, inputs: Dict[str, Any], label: str) -> Dict[str, Any]:
    store.log_event(actor=actor, event_type=f"agent_{label}_invoked", entity_id=entity_id, details={"inputs": inputs})
    return {"message": f"{label} executed (prototype stub)", "entity_id": entity_id}


AGENT_FUNCTIONS = {
    1: None,  # intent router is route_intent()
    2: None,  # orchestrator is orchestrate()
    3: None,  # approval is handled in workflow engine UI
    4: agent_4_demand_intake,
    5: agent_5_business_case,
    6: agent_6_portfolio,
    7: agent_7_program,
    8: agent_8_project_definition,
    9: agent_9_governance,
    10: agent_10_schedule,
    11: agent_11_resources,
    12: agent_12_financial,
    13: agent_13_vendor,
    14: agent_14_quality,
    15: agent_15_risk,
    16: agent_16_compliance,
    17: agent_17_change,
    18: agent_18_release,
    19: agent_19_knowledge,
    20: agent_20_improvement,
    21: agent_21_stakeholder,
    22: agent_22_analytics,
    23: agent_23_data_sync,
    24: agent_24_workflow_engine,
    25: agent_25_system_health,
}


def run_domain_agent(store: Store, *, agent_id: int, actor: str, entity_id: str | None, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Run a domain agent and record an agent_run entry."""
    from ..utils import json_dumps_compact

    started = now_iso()
    log_lines: List[str] = []
    try:
        if agent_id in (1, 2):
            raise ValueError("Use route_intent() or orchestrate() for agent 1/2")
        fn = AGENT_FUNCTIONS.get(agent_id)
        if not fn:
            out = agent_passthrough(store, actor=actor, entity_id=entity_id, inputs=inputs, label=f"Agent {agent_id}")
        else:
            # Some agents require entity_id, others can be global
            if agent_id in (23, 24, 25):
                out = fn(store, actor=actor, entity_id=entity_id, inputs=inputs)  # type: ignore
            else:
                if not entity_id:
                    raise ValueError("This agent requires an entity_id")
                out = fn(store, actor=actor, entity_id=entity_id, inputs=inputs)  # type: ignore
        ended = now_iso()
        store.record_agent_run(
            agent_id=agent_id,
            agent_name=f"Agent {agent_id}",
            entity_id=entity_id,
            actor=actor,
            started_at=started,
            ended_at=ended,
            status="success",
            inputs=inputs,
            outputs=out,
            log="\n".join(log_lines),
        )
        return out
    except Exception as e:
        ended = now_iso()
        store.record_agent_run(
            agent_id=agent_id,
            agent_name=f"Agent {agent_id}",
            entity_id=entity_id,
            actor=actor,
            started_at=started,
            ended_at=ended,
            status="error",
            inputs=inputs,
            outputs={"error": str(e)},
            log="\n".join(log_lines) + f"\nERROR: {e}",
        )
        raise
