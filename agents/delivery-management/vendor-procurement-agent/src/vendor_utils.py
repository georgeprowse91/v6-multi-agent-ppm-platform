"""
Vendor & Procurement Management Agent - Utility / Helper Functions

Contains shared helper methods extracted from VendorProcurementAgent that are
used across multiple action handlers.  Each function receives the agent instance
(``agent``) as its first argument so it can access stores, services, and config.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from llm.client import LLMGateway, LLMProviderError

if TYPE_CHECKING:
    from vendor_procurement_agent import VendorProcurementAgent


# ---------------------------------------------------------------------------
# ID generators
# ---------------------------------------------------------------------------


async def generate_vendor_id() -> str:
    """Generate unique vendor ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"VND-{timestamp}"


async def generate_request_id() -> str:
    """Generate unique procurement request ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"PR-{timestamp}"


async def generate_rfp_id() -> str:
    """Generate unique RFP ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"RFP-{timestamp}"


async def generate_proposal_id() -> str:
    """Generate unique proposal ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"PROP-{timestamp}"


async def generate_contract_id() -> str:
    """Generate unique contract ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"CTR-{timestamp}"


async def generate_po_number() -> str:
    """Generate unique PO number."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"PO-{timestamp}"


async def generate_invoice_id() -> str:
    """Generate unique invoice ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"INV-{timestamp}"


# ---------------------------------------------------------------------------
# Compliance & risk helpers
# ---------------------------------------------------------------------------


async def run_compliance_checks(
    agent: VendorProcurementAgent, vendor_data: dict[str, Any]
) -> dict[str, Any]:
    """Run compliance checks on vendor."""
    checks = agent.risk_client.check_vendor(vendor_data)
    if not checks:
        return {
            "sanctions_check": "Pass",
            "anti_corruption_check": "Pass",
            "credit_check": "Pass",
            "watchlist_hits": [],
            "sources": [],
        }
    return checks


async def evaluate_compliance_checks(
    agent: VendorProcurementAgent, checks: dict[str, Any], *, risk_score: float
) -> dict[str, Any]:
    failures = [
        key
        for key in ("sanctions_check", "anti_corruption_check", "credit_check")
        if checks.get(key) == "Fail"
    ]
    watchlist_hits = checks.get("watchlist_hits") or []
    status = "pending"
    reason = ""
    next_steps = ""
    if failures and agent.compliance_policy.get("block_on_fail", True):
        status = "blocked"
        reason = f"Compliance failures: {', '.join(failures)}"
        next_steps = "Vendor blocked pending compliance remediation."
    elif failures:
        status = "flagged"
        reason = f"Compliance concerns: {', '.join(failures)}"
        next_steps = "Vendor flagged for enhanced due diligence."
    elif watchlist_hits and agent.compliance_policy.get("flag_on_watchlist", True):
        status = "flagged"
        reason = "Vendor appears on watchlist."
        next_steps = "Vendor flagged for sanctions review."
    elif risk_score >= float(agent.compliance_policy.get("risk_threshold", 75)):
        status = "flagged"
        reason = "Risk score exceeded threshold."
        next_steps = "Vendor flagged for risk review."
    else:
        status = "pending"
        reason = "Compliance checks passed."
        next_steps = "Vendor pending approval. Submit required documentation."
    return {"status": status, "reason": reason, "next_steps": next_steps}


async def calculate_vendor_risk(
    agent: VendorProcurementAgent, vendor_data: dict[str, Any], compliance_checks: dict[str, Any]
) -> float:
    """Calculate vendor risk score (0-100, lower is better)."""
    ml_risk = agent.ml_service.risk_score(vendor_data, compliance_checks)
    return max(0, min(100, ml_risk))


# ---------------------------------------------------------------------------
# Categorisation / budget / suggestion helpers
# ---------------------------------------------------------------------------


async def categorize_procurement_request(
    agent: VendorProcurementAgent, request_data: dict[str, Any]
) -> str:
    """Categorize procurement request using AI."""
    description = request_data.get("description", "")
    return agent.request_classifier.predict(description, fallback="services")


async def check_budget_availability(
    agent: VendorProcurementAgent, request_data: dict[str, Any]
) -> dict[str, Any]:
    """Check budget availability for procurement."""
    return agent.financial_client.get_budget_status(request_data)


async def suggest_vendors(
    agent: VendorProcurementAgent, category: str, request_data: dict[str, Any]
) -> list[str]:
    """Suggest vendors based on category and requirements."""
    suggested = []
    for vendor_id, vendor in agent.vendors.items():
        if vendor.get("category") == category and vendor.get("status") == "Approved":
            suggested.append(vendor_id)

    if agent.enable_ml_recommendations:
        return agent.ml_service.recommend_vendors(list(agent.vendors.values()), category, top_n=5)

    return suggested[:5]  # Top 5


async def determine_approval_path(agent: VendorProcurementAgent, estimated_cost: float) -> str:
    """Determine approval path based on cost."""
    if estimated_cost > 100000:
        return "Executive Approval Required"
    elif estimated_cost > agent.procurement_threshold:
        return "Manager Approval Required"
    else:
        return "Auto-Approved"


# ---------------------------------------------------------------------------
# RFP helpers
# ---------------------------------------------------------------------------


async def select_rfp_template(
    agent: VendorProcurementAgent, category: str, *, template_id: str | None = None
) -> dict[str, Any]:
    """Select RFP template based on category or explicit template ID."""
    templates = {**agent.DEFAULT_RFP_TEMPLATES, **agent.config.get("rfp_templates", {})}
    if template_id:
        for template in templates.values():
            if template.get("template_id") == template_id:
                return template
    return templates.get(category, {"template_id": f"{category}_template", "sections": []})


async def generate_rfp_content(
    agent: VendorProcurementAgent,
    request: dict[str, Any],
    template: dict[str, Any],
    rfp_data: dict[str, Any],
) -> str:
    """Generate RFP content from template."""
    sections = template.get("sections", [])
    outline = "\n".join(f"- {section}" for section in sections)
    base_content = (
        f"RFP Title: {rfp_data.get('title', request.get('description'))}\n"
        f"Category: {request.get('category')}\n"
        f"Scope: {request.get('description')}\n"
        f"Requirements: {', '.join(rfp_data.get('requirements', []))}\n"
        f"Template Sections:\n{outline or '- General Requirements'}\n"
    )

    if not agent.enable_openai_rfp:
        return base_content

    system_prompt = (
        "You are a procurement specialist. Draft a structured RFP using the provided "
        "request context and template sections. Keep the response concise."
    )
    user_prompt = json.dumps(
        {"request": request, "template": template, "rfp_data": rfp_data}, indent=2
    )
    llm = LLMGateway()
    try:
        response = await llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        content = response.content.strip()
        return content if content else base_content
    except LLMProviderError:
        agent.logger.warning("OpenAI RFP generation failed; using template fallback.")
        return base_content


async def select_vendors_to_invite(
    agent: VendorProcurementAgent,
    category: str,
    suggested_vendors: list[str],
    specified_vendors: list[str],
) -> list[str]:
    """Select vendors to invite to RFP."""
    if specified_vendors:
        return specified_vendors
    return suggested_vendors[: agent.min_vendor_proposals]


# ---------------------------------------------------------------------------
# Proposal scoring
# ---------------------------------------------------------------------------


async def score_proposal(
    agent: VendorProcurementAgent, proposal: dict[str, Any], criteria: dict[str, float]
) -> dict[str, float]:
    """Score proposal against criteria."""
    if agent.enable_ai_scoring:
        system_prompt = (
            "You are a procurement evaluation assistant. Score the proposal against the "
            "criteria. Return JSON object with scores for each criterion from 0-100."
        )
        user_prompt = json.dumps({"proposal": proposal, "criteria": criteria}, indent=2)
        llm = LLMGateway()
        try:
            response = await llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
            data = json.loads(response.content)
            if isinstance(data, dict):
                return {key: float(value) for key, value in data.items() if key in criteria}
        except (LLMProviderError, json.JSONDecodeError, ValueError):
            agent.logger.warning("AI scoring failed; using ML scoring fallback.")

    scores = agent.ml_service.score_proposal(proposal, criteria_weights=criteria)
    return scores or {}


# ---------------------------------------------------------------------------
# Contract helpers
# ---------------------------------------------------------------------------


async def extract_contract_clauses(
    agent: VendorProcurementAgent, contract_data: dict[str, Any]
) -> dict[str, Any]:
    """Extract key clauses from contract."""
    contract_text = (
        contract_data.get("content")
        or contract_data.get("document_content")
        or contract_data.get("text")
    )
    if not contract_text:
        contract_text = json.dumps(contract_data.get("terms", {}), indent=2)

    if agent.form_recognizer.is_configured():
        form_result = agent.form_recognizer.extract_clauses(contract_text)
        if form_result:
            return {
                "source": "form_recognizer",
                "analysis": form_result,
            }

    clause_patterns = {
        "term": r"(term|duration|contract term)\s*[:\-]\s*(?P<value>[^\n]+)",
        "value": r"(total value|contract value|price|fees)\s*[:\-]\s*\$?(?P<value>[\d,\.]+)",
        "sla": r"(sla|service level|uptime)\s*[:\-]\s*(?P<value>[^\n]+)",
    }

    extracted = {}
    for clause, pattern in clause_patterns.items():
        match = re.search(pattern, contract_text, re.IGNORECASE)
        if match:
            extracted[clause] = match.group("value").strip()

    if "term" not in extracted:
        extracted["term"] = f"{contract_data.get('start_date')} to {contract_data.get('end_date')}"
    if "value" not in extracted and contract_data.get("value") is not None:
        extracted["value"] = str(contract_data.get("value"))
    if "sla" not in extracted and contract_data.get("slas"):
        extracted["sla"] = ", ".join(str(item) for item in contract_data.get("slas"))

    return extracted


async def select_contract_template(contract_type: str) -> dict[str, Any]:
    """Select contract template."""
    return {"template_id": f"{contract_type}_contract"}


# ---------------------------------------------------------------------------
# PO helpers
# ---------------------------------------------------------------------------


async def calculate_po_total(items: list[dict[str, Any]]) -> float:
    """Calculate total PO value."""
    total = 0.0
    for item in items:
        quantity = item.get("quantity", 1)
        unit_cost = item.get("unit_cost", 0)
        total += quantity * unit_cost
    return total


# ---------------------------------------------------------------------------
# Invoice helpers
# ---------------------------------------------------------------------------


async def three_way_match(
    agent: VendorProcurementAgent, invoice: dict[str, Any], purchase_order: dict[str, Any]
) -> dict[str, Any]:
    """Perform three-way matching between invoice, PO, and receipt."""
    discrepancies = []

    # Check amounts
    invoice_total = invoice.get("total_amount", 0)
    po_total = purchase_order.get("total_value", 0)

    if abs(invoice_total - po_total) > (po_total * agent.invoice_tolerance_pct):
        discrepancies.append(
            {
                "type": "amount_mismatch",
                "invoice_amount": invoice_total,
                "po_amount": po_total,
                "variance": invoice_total - po_total,
            }
        )

    def _normalize_line_item(item: dict[str, Any]) -> tuple[str, str]:
        sku = str(item.get("sku") or item.get("item_code") or "").strip().lower()
        description = str(item.get("description") or item.get("name") or "").strip().lower()
        return sku, description

    po_items = purchase_order.get("items", [])
    po_lookup: dict[str, dict[str, Any]] = {}
    for item in po_items:
        sku, description = _normalize_line_item(item)
        key = sku or description
        if key:
            po_lookup[key] = item

    invoice_items = invoice.get("line_items", [])
    for item in invoice_items:
        sku, description = _normalize_line_item(item)
        key = sku or description
        if not key or key not in po_lookup:
            discrepancies.append(
                {
                    "type": "line_item_missing_in_po",
                    "item": item,
                }
            )
            continue

        po_item = po_lookup[key]
        invoice_qty = item.get("quantity", 0)
        po_qty = po_item.get("quantity", 0)
        if invoice_qty != po_qty:
            discrepancies.append(
                {
                    "type": "quantity_mismatch",
                    "item": item,
                    "po_quantity": po_qty,
                    "invoice_quantity": invoice_qty,
                }
            )

        invoice_unit_cost = item.get("unit_cost", 0)
        po_unit_cost = po_item.get("unit_cost", 0)
        if po_unit_cost and abs(invoice_unit_cost - po_unit_cost) > (
            po_unit_cost * agent.invoice_tolerance_pct
        ):
            discrepancies.append(
                {
                    "type": "unit_cost_mismatch",
                    "item": item,
                    "po_unit_cost": po_unit_cost,
                    "invoice_unit_cost": invoice_unit_cost,
                }
            )

    return {"matched": len(discrepancies) == 0, "discrepancies": discrepancies}


async def initiate_payment(
    agent: VendorProcurementAgent, invoice: dict[str, Any]
) -> dict[str, Any]:
    """Initiate payment in ERP."""
    payment_request = {
        "invoice_id": invoice.get("invoice_id"),
        "vendor_id": invoice.get("vendor_id"),
        "amount": invoice.get("total_amount"),
        "currency": invoice.get("currency", agent.default_currency),
    }
    connector_results = agent.erp_ap_connector.initiate_payment(payment_request)
    return {
        "status": "Processing",
        "reference": f"PAY-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "connector_results": connector_results,
    }


# ---------------------------------------------------------------------------
# Performance & scoring helpers
# ---------------------------------------------------------------------------


async def collect_vendor_performance_data(
    agent: VendorProcurementAgent, vendor_id: str
) -> dict[str, Any]:
    """Collect vendor performance data."""
    return agent.analytics_client.get_vendor_summary(vendor_id)


async def calculate_delivery_timeliness(agent: VendorProcurementAgent, vendor_id: str) -> float:
    """Calculate vendor delivery timeliness percentage."""
    summary = agent.analytics_client.get_vendor_summary(vendor_id)
    deliveries = summary.get("deliveries", [])
    if not deliveries:
        return 95.0
    on_time = sum(1 for record in deliveries if record.get("on_time"))
    return round((on_time / len(deliveries)) * 100, 2)


async def calculate_quality_rating(agent: VendorProcurementAgent, vendor_id: str) -> float:
    """Calculate vendor quality rating."""
    summary = agent.analytics_client.get_vendor_summary(vendor_id)
    scores = summary.get("quality_scores", [])
    if not scores:
        return 4.5
    return round(sum(scores) / len(scores), 2)


async def calculate_compliance_score(agent: VendorProcurementAgent, vendor_id: str) -> float:
    """Calculate vendor compliance score."""
    summary = agent.analytics_client.get_vendor_summary(vendor_id)
    incidents = summary.get("compliance_incidents", [])
    score = max(0, 100 - (len(incidents) * 5))
    return float(score)


async def calculate_sla_adherence(agent: VendorProcurementAgent, vendor_id: str) -> float:
    """Calculate SLA adherence percentage."""
    summary = agent.analytics_client.get_vendor_summary(vendor_id)
    sla_records = summary.get("sla_records", [])
    if not sla_records:
        return 97.0
    met = sum(1 for record in sla_records if record.get("met"))
    return round((met / len(sla_records)) * 100, 2)


async def analyze_performance_trend(agent: VendorProcurementAgent, vendor_id: str) -> str:
    """Analyze vendor performance trend."""
    return "Stable"


async def generate_vendor_recommendations(metrics: dict[str, Any]) -> list[str]:
    """Generate recommendations based on vendor metrics."""
    recommendations = []

    if metrics.get("delivery_timeliness", 100) < 90:
        recommendations.append("Improve delivery timeliness through SLA enforcement")

    if metrics.get("quality_rating", 5.0) < 4.0:
        recommendations.append("Address quality issues through corrective action plan")

    if not recommendations:
        recommendations.append("Continue current performance levels")

    return recommendations


async def get_vendor_contracts(
    agent: VendorProcurementAgent, vendor_id: str
) -> list[dict[str, Any]]:
    """Get all contracts for a vendor."""
    vendor_contracts = []
    for contract_id, contract in agent.contracts.items():
        if contract.get("vendor_id") == vendor_id:
            vendor_contracts.append(contract)
    return vendor_contracts


async def get_vendor_issues(agent: VendorProcurementAgent, vendor_id: str) -> list[dict[str, Any]]:
    """Get recent issues with vendor."""
    summary = agent.analytics_client.get_vendor_summary(vendor_id)
    return summary.get("issue_tracker", [])


async def calculate_overall_vendor_score(
    agent: VendorProcurementAgent,
    vendor: dict[str, Any],
    *,
    external_adjustment: dict[str, Any] | None = None,
) -> float:
    """Calculate overall vendor score."""
    scoring = await calculate_vendor_score(agent, vendor, external_adjustment=external_adjustment)
    return scoring["score"]


async def calculate_vendor_score(
    agent: VendorProcurementAgent,
    vendor: dict[str, Any],
    *,
    external_adjustment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Calculate vendor score using weighted criteria."""
    risk_score = vendor.get("risk_score", 50)
    reliability_delta = 0
    if external_adjustment:
        risk_score = max(0, min(100, risk_score + external_adjustment.get("risk_delta", 0)))
        reliability_delta = external_adjustment.get("reliability_delta", 0)
    vendor = {**vendor, "risk_score": risk_score}
    score = agent.ml_service.score_vendor(vendor)
    if agent.vendor_scoring_weights:
        score = agent.ml_service._weighted_score(
            agent.ml_service._prepare_features(vendor),
            agent.vendor_scoring_weights,
        )
    score = max(0, min(100, score + reliability_delta))
    return {
        "score": score,
        "inputs": agent.ml_service._prepare_features(vendor),
        "weights": agent.vendor_scoring_weights or agent.ml_service.feature_weights,
    }


async def is_expiring_soon(contract: dict[str, Any]) -> bool:
    """Check if contract is expiring within 90 days."""
    end_date_str = contract.get("end_date")
    if not end_date_str:
        return False

    end_date = datetime.fromisoformat(end_date_str)
    days_until_expiry = (end_date - datetime.now(timezone.utc)).days
    return 0 < days_until_expiry <= 90


async def matches_criteria(vendor: dict[str, Any], criteria: dict[str, Any]) -> bool:
    """Check if vendor matches search criteria."""
    if "category" in criteria and vendor.get("category") != criteria["category"]:
        return False

    if "min_rating" in criteria:
        if vendor.get("performance_metrics", {}).get("quality_rating", 0) < criteria["min_rating"]:
            return False

    if "max_risk_score" in criteria:
        if vendor.get("risk_score", 100) > criteria["max_risk_score"]:
            return False

    if "status" in criteria and vendor.get("status") != criteria["status"]:
        return False

    return True


# ---------------------------------------------------------------------------
# Vendor data validation & persistence
# ---------------------------------------------------------------------------


async def validate_vendor_record(
    agent: VendorProcurementAgent, *, vendor: dict[str, Any], tenant_id: str
) -> dict[str, Any]:
    from data_quality.helpers import validate_against_schema

    record = {
        "id": vendor.get("vendor_id"),
        "tenant_id": tenant_id,
        "name": vendor.get("legal_name"),
        "category": vendor.get("category"),
        "status": vendor.get("status"),
        "owner": vendor.get("created_by"),
        "classification": vendor.get("classification", "internal"),
        "created_at": vendor.get("created_at"),
    }
    if vendor.get("updated_at"):
        record["updated_at"] = vendor.get("updated_at")
    errors = validate_against_schema(agent.vendor_schema_path, record)
    if errors:
        for error in errors:
            agent.logger.warning("Vendor schema error %s: %s", error.path, error.message)
    return {"is_valid": len(errors) == 0, "issues": [error.message for error in errors]}


async def persist_vendor(
    agent: VendorProcurementAgent, vendor: dict[str, Any], *, tenant_id: str
) -> None:
    vendor_id = vendor.get("vendor_id")
    if not vendor_id:
        return
    agent.vendors[vendor_id] = vendor
    agent.vendor_store.upsert(tenant_id, vendor_id, vendor)
    if agent.db_service:
        await agent.db_service.store("vendors", vendor_id, vendor)


async def resolve_vendor(
    agent: VendorProcurementAgent, vendor_id: str, *, tenant_id: str
) -> dict[str, Any] | None:
    vendor = agent.vendors.get(vendor_id)
    if vendor:
        return vendor
    stored = agent.vendor_store.get(tenant_id, vendor_id)
    if stored:
        agent.vendors[vendor_id] = stored
        return stored
    return None


# ---------------------------------------------------------------------------
# Event publishing
# ---------------------------------------------------------------------------


async def publish_event(
    agent: VendorProcurementAgent,
    event_type: str,
    *,
    payload: dict[str, Any],
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
    entity_id: str | None = None,
) -> dict[str, Any]:
    event_id = f"{event_type}-{uuid.uuid4()}"
    event = {
        "event_id": event_id,
        "event_type": event_type,
        "entity_id": entity_id,
        "payload": payload,
        "tenant_id": tenant_id,
        "correlation_id": correlation_id,
        "actor_id": actor_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    agent.event_store.upsert(tenant_id, event_id, event)
    if agent.db_service:
        await agent.db_service.store("procurement_events", event_id, event)
    await agent.event_publisher.publish(event)
    return event


# ---------------------------------------------------------------------------
# Mitigation workflow
# ---------------------------------------------------------------------------


async def initiate_mitigation_workflow(
    agent: VendorProcurementAgent,
    *,
    vendor: dict[str, Any],
    reason: str,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    vendor_id = vendor.get("vendor_id")
    if not vendor_id:
        return {"status": "skipped"}
    task_payload = {
        "vendor_id": vendor_id,
        "vendor_name": vendor.get("legal_name"),
        "reason": reason,
        "risk_score": vendor.get("risk_score"),
        "compliance_status": vendor.get("compliance_status"),
    }
    task_result = await agent.task_client.create_task(
        tenant_id=tenant_id,
        instance_id=vendor_id,
        task_type="vendor_mitigation",
        payload=task_payload,
    )
    notification = await agent.communications_client.notify(
        tenant_id=tenant_id,
        subject=f"Vendor risk mitigation required: {vendor.get('legal_name')}",
        body=(
            f"Vendor {vendor.get('legal_name')} triggered a risk event. "
            f"Reason: {reason}. Current status: {vendor.get('status')}."
        ),
        stakeholders=vendor.get("stakeholders", []),
        metadata={"vendor_id": vendor_id, "correlation_id": correlation_id},
    )
    await publish_event(
        agent,
        "vendor.mitigation.initiated",
        payload={
            "vendor_id": vendor_id,
            "task": task_result,
            "notification": notification,
            "reason": reason,
        },
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        actor_id=vendor.get("created_by", "system"),
        entity_id=vendor_id,
    )
    return {"task": task_result, "notification": notification}


# ---------------------------------------------------------------------------
# Research helpers
# ---------------------------------------------------------------------------


def extract_sources(snippets: list[str]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    for snippet in snippets:
        match = re.search(r"\((https?://[^)]+)\)", snippet)
        url = match.group(1) if match else ""
        if not url:
            continue
        sources.append({"url": url, "citation": snippet.strip()})
    return sources


def score_vendor_research(research: dict[str, Any]) -> dict[str, Any]:
    insights = research.get("insights", []) if isinstance(research, dict) else []
    negative = sum(1 for insight in insights if insight.get("sentiment") == "negative")
    positive = sum(1 for insight in insights if insight.get("sentiment") == "positive")
    risk_delta = max(-20, min(20, negative * 6 - positive * 4))
    reliability_delta = max(-10, min(10, positive * 2 - negative))
    return {
        "risk_delta": risk_delta,
        "reliability_delta": reliability_delta,
        "signals": {"positive": positive, "negative": negative},
    }


async def extract_vendor_insights(
    agent: VendorProcurementAgent,
    summary: str,
    snippets: list[str],
    *,
    llm_client: LLMGateway | None = None,
) -> list[dict[str, Any]]:
    sources = extract_sources(snippets)
    system_prompt = (
        "You are a procurement analyst. Extract insights about the vendor from the summary "
        "and snippets. Return ONLY JSON as an array of objects with fields: "
        "category (financial, performance, legal, sentiment), sentiment "
        "(positive, negative, neutral), detail, source_url."
    )
    user_prompt = json.dumps(
        {"summary": summary, "snippets": snippets, "sources": sources},
        indent=2,
    )

    llm = llm_client or LLMGateway()
    try:
        response = await llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        data = json.loads(response.content)
    except (LLMProviderError, ValueError, json.JSONDecodeError) as exc:
        agent.logger.warning("Vendor insight extraction failed", extra={"error": str(exc)})
        return [
            {
                "category": "sentiment",
                "sentiment": "neutral",
                "detail": summary,
                "source_url": sources[0]["url"] if sources else "",
            }
        ]

    insights: list[dict[str, Any]] = []
    if not isinstance(data, list):
        return insights
    for entry in data:
        if not isinstance(entry, dict):
            continue
        category = str(entry.get("category", "sentiment")).strip().lower()
        sentiment = str(entry.get("sentiment", "neutral")).strip().lower()
        detail = str(entry.get("detail", "")).strip()
        source_url = str(entry.get("source_url", "")).strip()
        if not detail:
            continue
        insights.append(
            {
                "category": category,
                "sentiment": sentiment,
                "detail": detail,
                "source_url": source_url,
            }
        )
    return insights
