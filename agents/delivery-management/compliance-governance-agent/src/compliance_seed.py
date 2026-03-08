"""
Compliance & Regulatory Agent - Seed Data and Schema Definitions

Contains the initial regulatory frameworks, control definitions,
and compliance schema definitions used during agent initialization.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import requests
from compliance_utils import extract_effective_date, extract_obligations_from_text

if TYPE_CHECKING:
    from compliance_regulatory_agent import ComplianceRegulatoryAgent


# ---------------------------------------------------------------------------
# Seed frameworks & controls
# ---------------------------------------------------------------------------

SEED_FRAMEWORKS: dict[str, dict[str, Any]] = {
    "REG-ISO-27001": {
        "name": "ISO 27001",
        "description": "Information security management system requirements.",
        "jurisdiction": ["global"],
        "industry": ["technology", "finance", "healthcare", "public"],
        "data_sensitivity": ["medium", "high"],
        "effective_date": "2022-10-25",
        "related_controls": [],
        "applicability_rules": {
            "applies_to_all": True,
            "jurisdiction_filter": ["global"],
            "industry_filter": [],
            "data_sensitivity_filter": ["medium", "high"],
        },
    },
    "REG-SOC-2": {
        "name": "SOC 2",
        "description": "Trust Services Criteria for service organizations.",
        "jurisdiction": ["global"],
        "industry": ["technology", "services", "saas"],
        "data_sensitivity": ["medium", "high"],
        "effective_date": "2017-05-01",
        "related_controls": [],
        "applicability_rules": {
            "applies_to_all": False,
            "jurisdiction_filter": [],
            "industry_filter": ["technology", "services", "saas"],
            "data_sensitivity_filter": ["medium", "high"],
        },
    },
    "REG-PRIVACY-ACT-AU": {
        "name": "Privacy Act 1988 (Cth)",
        "description": "Australian Privacy Act 1988 including the Australian Privacy Principles (APPs).",
        "jurisdiction": ["au"],
        "industry": [],
        "data_sensitivity": ["high"],
        "effective_date": "1988-12-21",
        "related_controls": [],
        "applicability_rules": {
            "applies_to_all": False,
            "jurisdiction_filter": ["au"],
            "industry_filter": [],
            "data_sensitivity_filter": ["high"],
        },
    },
}

SEED_CONTROLS: list[dict[str, Any]] = [
    {
        "control_id": "CTL-ISO-01",
        "description": "Maintain an information security policy approved by management.",
        "regulation": "REG-ISO-27001",
        "control_type": "preventive",
        "owner": "security",
        "requirements": ["implemented", "evidence"],
        "test_frequency": "annually",
    },
    {
        "control_id": "CTL-ISO-02",
        "description": "Perform regular risk assessments and document mitigations.",
        "regulation": "REG-ISO-27001",
        "control_type": "detective",
        "owner": "risk",
        "requirements": ["implemented", "risk_mitigation", "evidence"],
        "test_frequency": "quarterly",
    },
    {
        "control_id": "CTL-SOC2-01",
        "description": "Monitor system availability and incident response.",
        "regulation": "REG-SOC-2",
        "control_type": "detective",
        "owner": "operations",
        "requirements": ["implemented", "quality_tests", "evidence"],
        "test_frequency": "quarterly",
    },
    {
        "control_id": "CTL-SOC2-02",
        "description": "Maintain audit logs for changes and access.",
        "regulation": "REG-SOC-2",
        "control_type": "preventive",
        "owner": "security",
        "requirements": ["implemented", "audit_logs", "evidence"],
        "test_frequency": "monthly",
    },
    {
        "control_id": "CTL-PRIVACY-AU-01",
        "description": "Conduct privacy impact assessments for personal information under APP obligations.",
        "regulation": "REG-PRIVACY-ACT-AU",
        "control_type": "preventive",
        "owner": "privacy",
        "requirements": ["implemented", "data_privacy", "evidence"],
        "test_frequency": "annually",
    },
    {
        "control_id": "CTL-PRIVACY-AU-02",
        "description": "Ensure APP access and correction requests are tracked and fulfilled within statutory timelines.",
        "regulation": "REG-PRIVACY-ACT-AU",
        "control_type": "detective",
        "owner": "privacy",
        "requirements": ["implemented", "quality_tests", "evidence"],
        "test_frequency": "quarterly",
    },
]

COMPLIANCE_SCHEMAS: dict[str, dict[str, str]] = {
    "regulatory_frameworks": {
        "framework_id": "string",
        "name": "string",
        "description": "string",
        "jurisdiction": "list[string]",
        "industry": "list[string]",
        "data_sensitivity": "list[string]",
        "effective_date": "string",
        "applicability_rules": "json",
    },
    "control_requirements": {
        "control_id": "string",
        "regulation_id": "string",
        "description": "string",
        "owner": "string",
        "control_type": "string",
        "requirements": "list[string]",
        "evidence_requirements": "list[string]",
        "test_frequency": "string",
    },
    "control_mappings": {
        "mapping_id": "string",
        "project_id": "string",
        "industry": "string",
        "geography": "string",
        "data_sensitivity": "string",
        "control_ids": "list[string]",
        "created_at": "string",
    },
    "compliance_evidence": {
        "evidence_id": "string",
        "control_id": "string",
        "project_id": "string",
        "source_agent": "string",
        "metadata": "json",
        "created_at": "string",
    },
    "compliance_reports": {
        "report_id": "string",
        "report_type": "string",
        "framework": "string",
        "generated_at": "string",
        "report_url": "string",
    },
}


async def seed_regulatory_frameworks(agent: ComplianceRegulatoryAgent) -> None:
    """Populate the agent's regulation library and control registry with seed data."""
    if agent.regulation_library or agent.control_registry:
        return
    if agent.config and not agent.config.get("seed_frameworks", True):
        return

    import copy

    frameworks = copy.deepcopy(SEED_FRAMEWORKS)

    for regulation_id, regulation in frameworks.items():
        regulation["regulation_id"] = regulation_id
        regulation["created_at"] = datetime.now(timezone.utc).isoformat()
        agent.regulation_library[regulation_id] = regulation
        await agent.db_service.store("regulations", regulation_id, regulation)

    for control in SEED_CONTROLS:
        control_id = control["control_id"]
        control_payload = {
            **control,
            "evidence_requirements": control.get("evidence_requirements", []),
            "status": "Active",
            "last_test_date": None,
            "last_test_result": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        agent.control_registry[control_id] = control_payload
        regulation_id = control_payload.get("regulation")
        if regulation_id in agent.regulation_library:
            agent.regulation_library[regulation_id]["related_controls"].append(control_id)
        await agent.db_service.store("controls", control_id, control_payload)


async def define_compliance_schemas(agent: ComplianceRegulatoryAgent) -> None:
    """Store compliance schemas in the agent and persist to DB."""
    agent.compliance_schemas = dict(COMPLIANCE_SCHEMAS)
    for schema_id, schema in COMPLIANCE_SCHEMAS.items():
        await agent.db_service.store("compliance_schema", schema_id, schema)


# ---------------------------------------------------------------------------
# Azure Cognitive Services helpers
# ---------------------------------------------------------------------------


async def extract_regulation_metadata(
    agent: ComplianceRegulatoryAgent, regulation_data: dict[str, Any]
) -> dict[str, Any]:
    text = regulation_data.get("text") or ""
    document_url = regulation_data.get("document_url")
    document_content = regulation_data.get("document_content")

    extracted_text = text
    metadata: dict[str, Any] = {}
    if document_url or document_content:
        document_result = await analyze_document_intelligence(
            agent, document_url=document_url, document_content=document_content
        )
        extracted_text = document_result.get("content") or extracted_text
        metadata["document_intelligence"] = document_result

    text_analytics_result = await analyze_text_analytics(agent, extracted_text)
    metadata["text_analytics"] = text_analytics_result

    obligations = extract_obligations_from_text(
        extracted_text, text_analytics_result.get("key_phrases", [])
    )
    effective_date = extract_effective_date(text_analytics_result.get("entities", []))

    return {"obligations": obligations, "effective_date": effective_date, "metadata": metadata}


async def analyze_text_analytics(agent: ComplianceRegulatoryAgent, text: str) -> dict[str, Any]:
    endpoint = agent.config.get("text_analytics_endpoint") if agent.config else None
    api_key = agent.config.get("text_analytics_key") if agent.config else None
    endpoint = endpoint or os.getenv("AZURE_TEXT_ANALYTICS_ENDPOINT")
    api_key = api_key or os.getenv("AZURE_TEXT_ANALYTICS_KEY")
    if not endpoint or not api_key or not text:
        return {"key_phrases": [], "entities": []}

    text_payload = {"documents": [{"id": "1", "language": "en", "text": text[:5000]}]}
    headers = {"Ocp-Apim-Subscription-Key": api_key, "Content-Type": "application/json"}

    async def _post(path: str) -> dict[str, Any]:
        response = await asyncio.to_thread(
            requests.post,
            f"{endpoint.rstrip('/')}/{path}",
            headers=headers,
            json=text_payload,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    try:
        key_phrases_response = await _post("text/analytics/v3.1/keyPhrases")
        entities_response = await _post("text/analytics/v3.1/entities/recognition/general")
    except requests.RequestException as exc:
        agent.logger.warning("Text analytics failed", extra={"error": str(exc)})
        return {"key_phrases": [], "entities": []}

    key_phrases = (
        key_phrases_response.get("documents", [{}])[0].get("keyPhrases", [])
        if isinstance(key_phrases_response, dict)
        else []
    )
    entities = (
        entities_response.get("documents", [{}])[0].get("entities", [])
        if isinstance(entities_response, dict)
        else []
    )
    return {"key_phrases": key_phrases, "entities": entities}


async def analyze_document_intelligence(
    agent: ComplianceRegulatoryAgent,
    *,
    document_url: str | None,
    document_content: str | bytes | None,
) -> dict[str, Any]:
    endpoint = agent.config.get("document_intelligence_endpoint") if agent.config else None
    api_key = agent.config.get("document_intelligence_key") if agent.config else None
    endpoint = endpoint or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    api_key = api_key or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
    if not endpoint or not api_key or (not document_url and not document_content):
        return {"content": ""}

    headers = {"Ocp-Apim-Subscription-Key": api_key}
    analyze_url = f"{endpoint.rstrip('/')}/formrecognizer/documentModels/prebuilt-layout:analyze"
    params = {"api-version": "2023-07-31"}

    if document_url:
        request_body = {"urlSource": document_url}
        headers["Content-Type"] = "application/json"
        response = await asyncio.to_thread(
            requests.post,
            analyze_url,
            params=params,
            headers=headers,
            json=request_body,
            timeout=15,
        )
    else:
        if isinstance(document_content, str):
            document_bytes = document_content.encode("utf-8")
        else:
            document_bytes = document_content
        headers["Content-Type"] = "application/octet-stream"
        response = await asyncio.to_thread(
            requests.post,
            analyze_url,
            params=params,
            headers=headers,
            data=document_bytes,
            timeout=15,
        )

    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        agent.logger.warning("Document intelligence call failed", extra={"error": str(exc)})
        return {"content": ""}

    operation_location = response.headers.get("operation-location")
    if not operation_location:
        return {"content": ""}

    try:
        result_response = await asyncio.to_thread(
            requests.get,
            operation_location,
            headers={"Ocp-Apim-Subscription-Key": api_key},
            timeout=15,
        )
        result_response.raise_for_status()
        result_payload = result_response.json()
    except (requests.RequestException, ValueError) as exc:
        agent.logger.warning("Document intelligence result failed", extra={"error": str(exc)})
        return {"content": ""}

    content = result_payload.get("analyzeResult", {}).get("content", "")
    return {"content": content, "raw": result_payload}
