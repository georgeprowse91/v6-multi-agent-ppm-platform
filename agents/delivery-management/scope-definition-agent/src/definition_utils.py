"""
Stateless utility functions for the Project Definition & Scope Agent.

These helpers have no dependency on the agent instance and can be tested independently.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from definition_models import Requirement, TraceabilityEntry, WBSItem

# ---------------------------------------------------------------------------
# ID generators
# ---------------------------------------------------------------------------


async def generate_project_id() -> str:
    """Generate unique project ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"PRJ-{timestamp}-{uuid.uuid4().hex[:6]}"


async def generate_charter_id(project_id: str) -> str:
    """Generate unique charter ID."""
    return f"CHAR-{project_id}-{uuid.uuid4().hex[:6]}"


async def generate_wbs_id(project_id: str) -> str:
    """Generate unique WBS ID."""
    return f"{project_id}-WBS-001"


async def generate_baseline_id(project_id: str) -> str:
    """Generate unique baseline ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{project_id}-BASELINE-{timestamp}"


# ---------------------------------------------------------------------------
# Traceability helpers
# ---------------------------------------------------------------------------


def extract_wbs_item_ids(wbs_items: list[WBSItem]) -> list[str]:
    """Walk a WBS tree and collect all numeric-prefixed keys as item IDs."""
    ids: list[str] = []

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(key, str) and key and key[0].isdigit():
                    ids.append(key)
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(wbs_items)
    return ids


def generate_traceability_matrix(
    requirements: list[Requirement], wbs: list[WBSItem]
) -> list[TraceabilityEntry]:
    """Generate requirement-to-WBS traceability entries with coverage status."""
    wbs_item_ids = extract_wbs_item_ids(wbs)
    default_wbs = wbs_item_ids[0:1]

    entries: list[TraceabilityEntry] = []
    for requirement in requirements:
        requirement_id = requirement.get("id") or f"REQ-{uuid.uuid4().hex[:8]}"
        mapped_wbs_ids = requirement.get("wbs_ids") or default_wbs
        status = "covered" if mapped_wbs_ids else "not_covered"
        entries.append(
            {
                "requirement_id": requirement_id,
                "wbs_item_ids": mapped_wbs_ids,
                "coverage_status": status,
            }
        )
    return entries


# ---------------------------------------------------------------------------
# Search-query sanitization
# ---------------------------------------------------------------------------


def sanitize_search_query(objective: str) -> str:
    sanitized = objective.strip()
    if not sanitized:
        return ""

    sanitized = re.sub(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}",
        "[REDACTED_EMAIL]",
        sanitized,
    )
    sanitized = re.sub(r"\\b\\d{4,}\\b", "[REDACTED_ID]", sanitized)
    sanitized = re.sub(r"\\b[A-Z0-9]{10,}\\b", "[REDACTED_TOKEN]", sanitized)
    sanitized = sanitized.split("\\n", maxsplit=1)[0]
    return sanitized[:240]


# ---------------------------------------------------------------------------
# Serialization helpers (for search indexing)
# ---------------------------------------------------------------------------


def serialize_charter_for_index(charter: dict[str, Any]) -> str:
    document = charter.get("document", {})
    return (
        f"{charter.get('title', '')} "
        f"{document.get('executive_summary', '')} "
        f"{' '.join(document.get('objectives', []))} "
        f"{document.get('scope_overview', {})}"
    )


def serialize_wbs_for_index(wbs: dict[str, Any]) -> str:
    names = []
    for code, node in wbs.items():
        if isinstance(node, dict):
            names.append(f"{code} {node.get('name', '')}".strip())
    return " ".join(names)


def serialize_requirements_for_index(requirements: list[dict[str, Any]]) -> str:
    return " ".join(req.get("text", "") for req in requirements if req.get("text"))


def serialize_traceability_for_index(matrix: dict[str, Any]) -> str:
    requirements = matrix.get("requirements", [])
    return " ".join(req.get("text", "") for req in requirements if req.get("text"))


def serialize_raci_for_index(raci_matrix: dict[str, Any]) -> str:
    assignments = raci_matrix.get("assignments", [])
    return " ".join(
        f"{assignment.get('deliverable')}:{assignment.get('stakeholder')}"
        for assignment in assignments
    )


# ---------------------------------------------------------------------------
# Scope comparison helpers
# ---------------------------------------------------------------------------


def scope_to_text(scope: dict[str, Any]) -> str:
    return (
        f"In scope: {', '.join(scope.get('in_scope', []))}. "
        f"Out of scope: {', '.join(scope.get('out_of_scope', []))}. "
        f"Deliverables: {', '.join(scope.get('deliverables', []))}."
    )


# ---------------------------------------------------------------------------
# Response parsers (for OpenAI output)
# ---------------------------------------------------------------------------


def parse_wbs_response(response: str) -> dict[str, Any]:
    lines = [line.strip() for line in response.splitlines() if line.strip()]
    wbs: dict[str, Any] = {}
    for line in lines:
        if "-" in line:
            code, name = line.split("-", maxsplit=1)
            wbs[code.strip()] = {"name": name.strip(), "children": {}}
    return wbs


def parse_raci_response(response: str | None) -> list[dict[str, Any]]:
    if not response:
        return []
    assignments: list[dict[str, Any]] = []
    for line in response.splitlines():
        if "|" in line:
            parts = [part.strip() for part in line.split("|")]
            if len(parts) >= 3:
                assignments.append(
                    {
                        "deliverable": parts[0],
                        "stakeholder": parts[1],
                        "role": parts[2],
                    }
                )
    return assignments


# ---------------------------------------------------------------------------
# Charter content formatter
# ---------------------------------------------------------------------------


async def generate_charter_content(charter: dict[str, Any]) -> str:
    """Generate formatted charter content from template strings."""
    document = charter.get("document", {})
    title = charter.get("title", "Project Charter")
    project_id = charter.get("project_id", "unknown")
    created_at = charter.get("created_at", "")

    def format_list(items: list[Any]) -> str:
        if not items:
            return "None"
        return "\\n".join(f"- {item}" for item in items)

    scope = document.get("scope_overview", {})
    stakeholders = document.get("stakeholders", [])
    stakeholder_lines: list[str] = []
    for stakeholder in stakeholders:
        name = stakeholder.get("name") if isinstance(stakeholder, dict) else str(stakeholder)
        role = ""
        if isinstance(stakeholder, dict):
            role = stakeholder.get("role", "")
        stakeholder_lines.append(f"{name}{f' ({role})' if role else ''}")

    governance = document.get("governance_structure", {})
    governance_text = (
        f"Sponsor: {governance.get('sponsor', 'Unassigned')}\\n"
        f"Project Manager: {governance.get('project_manager', 'Unassigned')}\\n"
        f"Steering Committee: {', '.join(governance.get('steering_committee', [])) or 'None'}\\n"
        f"Reporting Frequency: {governance.get('reporting_frequency', 'weekly')}"
    )

    return (
        f"Project Charter\\n"
        f"Title: {title}\\n"
        f"Project ID: {project_id}\\n"
        f"Created At: {created_at}\\n"
        f"Status: {charter.get('status', 'Draft')}\\n"
        f"Methodology: {charter.get('methodology', 'hybrid')}\\n\\n"
        f"Executive Summary\\n{document.get('executive_summary', '')}\\n\\n"
        f"Objectives\\n{format_list(document.get('objectives', []))}\\n\\n"
        f"Scope Overview\\n"
        f"In Scope\\n{format_list(scope.get('in_scope', []))}\\n\\n"
        f"Out of Scope\\n{format_list(scope.get('out_of_scope', []))}\\n\\n"
        f"Deliverables\\n{format_list(scope.get('deliverables', []))}\\n\\n"
        f"High-Level Requirements\\n"
        f"{format_list(document.get('high_level_requirements', []))}\\n\\n"
        f"Stakeholders\\n{format_list(stakeholder_lines)}\\n\\n"
        f"Governance Structure\\n{governance_text}\\n\\n"
        f"Success Criteria\\n{format_list(document.get('success_criteria', []))}\\n\\n"
        f"Assumptions\\n{format_list(document.get('assumptions', []))}\\n\\n"
        f"Constraints\\n{format_list(document.get('constraints', []))}\\n"
    )
