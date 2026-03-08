"""Natural language to workflow definition parser.

Uses LLM to convert natural language descriptions into structured workflow
definitions, with validation and iterative refinement.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any

from agent_catalog import AGENT_CATALOG_BY_AGENT_ID

logger = logging.getLogger("workflow.nl_workflow")

# Canonical agent IDs from the agent catalog
VALID_AGENT_IDS = frozenset(AGENT_CATALOG_BY_AGENT_ID.keys())

# Mapping from NL prompt shorthand to canonical catalog IDs
_SHORTHAND_TO_CATALOG: dict[str, str] = {
    entry.agent_id.removesuffix("-agent"): entry.agent_id
    for entry in AGENT_CATALOG_BY_AGENT_ID.values()
}

NL_SYSTEM_PROMPT = """You are a workflow definition generator for a Project Portfolio Management system.
Convert the user's natural language description into a structured workflow definition.

Output valid JSON with this schema:
{
  "name": "string",
  "description": "string",
  "steps": [
    {
      "id": "string (UUID)",
      "type": "task|decision|approval|notification|parallel|api",
      "name": "string",
      "description": "string",
      "agent_id": "string (optional - the agent to handle this step)",
      "config": {},
      "transitions": [
        {"target": "step_id", "condition": "string (optional)"}
      ]
    }
  ]
}

Available step types:
- task: An action performed by an agent or user
- decision: A branching point with conditional transitions
- approval: Requires human approval before proceeding
- notification: Send a notification to stakeholders
- parallel: Execute multiple sub-steps concurrently
- api: Call an external API

Available agents (use these exact IDs):
- intent-router-agent: classifies user queries and routes to domain agents
- demand-intake-agent: handles demand intake and classification
- business-case-agent: business case analysis and evaluation
- portfolio-optimisation-agent: portfolio-level optimisation
- program-management-agent: program coordination and management
- scope-definition-agent: project scope definition and WBS
- lifecycle-governance-agent: lifecycle and gate governance
- schedule-planning-agent: schedule planning and optimisation
- resource-management-agent: resource allocation and planning
- financial-management-agent: financial review and budget management
- vendor-procurement-agent: vendor management and procurement
- quality-management-agent: quality assurance and control
- risk-management-agent: risk identification and mitigation
- compliance-governance-agent: compliance and regulatory governance
- change-control-agent: change request management
- release-deployment-agent: release and deployment management
- knowledge-management-agent: knowledge base management
- continuous-improvement-agent: retrospectives and process improvement
- stakeholder-communications-agent: stakeholder notifications and updates
- analytics-insights-agent: analytics and reporting
- data-synchronisation-agent: data sync across systems
- system-health-agent: platform health monitoring
- workspace-setup-agent: workspace initialisation and methodology bootstrap

Return ONLY the JSON, no markdown formatting."""

REFINE_PROMPT = """The user wants to modify this existing workflow definition.
Current definition:
{current_definition}

User feedback: {feedback}

Output the updated workflow definition as valid JSON. Return ONLY the JSON."""

# Keyword-to-agent mapping for the fallback parser.
# Each entry maps a set of trigger keywords to an agent ID, step type,
# step name, and step description.
_KEYWORD_AGENT_MAP: list[dict[str, Any]] = [
    {
        "keywords": ["risk", "threat", "vulnerab", "exposure", "hazard"],
        "agent_id": "risk-management-agent",
        "type": "decision",
        "name": "Risk Assessment Gate",
        "description": "Evaluate risk level and determine mitigation path",
        "branching": True,
    },
    {
        "keywords": ["approv", "sign-off", "authorize", "cfo", "executive", "gate"],
        "agent_id": None,
        "type": "approval",
        "name": "Executive Approval",
        "description": "Requires executive sign-off before proceeding",
        "config": {"approver_role": "executive"},
    },
    {
        "keywords": ["budget", "cost", "financ", "spend", "forecast", "revenue", "roi"],
        "agent_id": "financial-management-agent",
        "type": "task",
        "name": "Financial Review",
        "description": "Review budget implications, cost estimates, and financial forecasts",
    },
    {
        "keywords": ["compli", "regulat", "audit", "gdpr", "sox", "hipaa", "legal"],
        "agent_id": "compliance-governance-agent",
        "type": "task",
        "name": "Compliance Check",
        "description": "Verify regulatory compliance and governance requirements",
    },
    {
        "keywords": ["vendor", "procure", "supplier", "rfp", "contract", "outsourc"],
        "agent_id": "vendor-procurement-agent",
        "type": "task",
        "name": "Vendor & Procurement",
        "description": "Manage vendor selection, procurement, and contract processes",
    },
    {
        "keywords": ["scope", "requirement", "wbs", "deliverable", "objective"],
        "agent_id": "scope-definition-agent",
        "type": "task",
        "name": "Scope Definition",
        "description": "Define project scope, requirements, and work breakdown structure",
    },
    {
        "keywords": ["resource", "team", "staff", "allocat", "capacity", "skill"],
        "agent_id": "resource-management-agent",
        "type": "task",
        "name": "Resource Planning",
        "description": "Plan resource allocation, team assignments, and capacity",
    },
    {
        "keywords": ["quality", "test", "qa", "inspect", "defect", "standard"],
        "agent_id": "quality-management-agent",
        "type": "task",
        "name": "Quality Assurance",
        "description": "Define and execute quality assurance and testing procedures",
    },
    {
        "keywords": ["schedul", "timeline", "milestone", "deadline", "gantt", "plan"],
        "agent_id": "schedule-planning-agent",
        "type": "task",
        "name": "Schedule Planning",
        "description": "Create and optimise the project schedule and milestones",
    },
    {
        "keywords": ["change", "cr ", "change request", "impact analysis"],
        "agent_id": "change-control-agent",
        "type": "task",
        "name": "Change Control",
        "description": "Evaluate and manage change requests with impact analysis",
    },
    {
        "keywords": ["releas", "deploy", "rollout", "launch", "go-live"],
        "agent_id": "release-deployment-agent",
        "type": "task",
        "name": "Release & Deployment",
        "description": "Plan and execute release deployment and go-live activities",
    },
    {
        "keywords": ["knowledge", "lesson", "document", "wiki", "best practice"],
        "agent_id": "knowledge-management-agent",
        "type": "task",
        "name": "Knowledge Capture",
        "description": "Capture lessons learned and update knowledge base",
    },
    {
        "keywords": ["retro", "improv", "kaizen", "optimi", "efficien"],
        "agent_id": "continuous-improvement-agent",
        "type": "task",
        "name": "Continuous Improvement",
        "description": "Run retrospective and identify process improvements",
    },
    {
        "keywords": ["portfolio", "prioriti", "strategic", "alignment", "investment"],
        "agent_id": "portfolio-optimisation-agent",
        "type": "task",
        "name": "Portfolio Optimisation",
        "description": "Evaluate strategic alignment and portfolio-level prioritisation",
    },
    {
        "keywords": ["program", "cross-project", "dependency", "coordination"],
        "agent_id": "program-management-agent",
        "type": "task",
        "name": "Program Coordination",
        "description": "Coordinate cross-project dependencies and program alignment",
    },
    {
        "keywords": ["business case", "justif", "feasib", "benefit"],
        "agent_id": "business-case-agent",
        "type": "task",
        "name": "Business Case Analysis",
        "description": "Analyse business justification, feasibility, and expected benefits",
    },
    {
        "keywords": ["analytic", "report", "dashboard", "metric", "kpi", "insight"],
        "agent_id": "analytics-insights-agent",
        "type": "task",
        "name": "Analytics & Reporting",
        "description": "Generate analytics insights, dashboards, and KPI reports",
    },
]


def _generate_step_id() -> str:
    """Generate a unique step identifier."""
    return str(uuid.uuid4())


def _normalize_agent_id(raw_id: str | None) -> str | None:
    """Resolve an agent ID, accepting both shorthand and canonical forms."""
    if not raw_id:
        return None
    if raw_id in VALID_AGENT_IDS:
        return raw_id
    canonical = _SHORTHAND_TO_CATALOG.get(raw_id)
    if canonical:
        return canonical
    # Try appending "-agent" suffix
    with_suffix = f"{raw_id}-agent"
    if with_suffix in VALID_AGENT_IDS:
        return with_suffix
    return None


def _get_llm_gateway():
    """Lazy import to avoid circular deps."""
    try:
        from llm.client import LLMGateway

        provider = os.getenv("LLM_PROVIDER", "mock")
        config: dict[str, Any] = {}
        if provider == "mock":
            config["demo_mode"] = True
        return LLMGateway(provider=provider, config=config)
    except Exception as exc:
        logger.warning("LLMGateway init failed: %s", exc)
        return None


async def _llm_complete(system_prompt: str, user_prompt: str) -> str:
    """Call LLM and return content, or empty string on failure."""
    gateway = _get_llm_gateway()
    if gateway is None:
        return ""
    try:
        response = await gateway.complete(system_prompt, user_prompt)
        return response.content
    except Exception as exc:
        logger.warning("LLM call failed: %s", exc)
        return ""


def _parse_json_response(raw: str) -> dict[str, Any]:
    """Parse JSON from LLM response, stripping markdown fences if present."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        cleaned = "\n".join(lines)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {}


def _sanitise_llm_definition(definition: dict[str, Any]) -> dict[str, Any]:
    """Normalise agent IDs in an LLM-generated definition against the catalog."""
    steps = definition.get("steps", [])
    step_id_remap: dict[str, str] = {}

    for step in steps:
        old_id = step.get("id", "")
        if not old_id or old_id in step_id_remap:
            new_id = _generate_step_id()
        else:
            new_id = old_id
        step_id_remap[old_id] = new_id
        step["id"] = new_id

        raw_agent = step.get("agent_id")
        if raw_agent:
            resolved = _normalize_agent_id(raw_agent)
            if resolved:
                step["agent_id"] = resolved
            else:
                logger.warning(
                    "LLM generated unknown agent_id %r in step %r; removing",
                    raw_agent,
                    step.get("name"),
                )
                del step["agent_id"]

    # Re-map transition targets to new IDs
    for step in steps:
        for transition in step.get("transitions", []):
            target = transition.get("target")
            if target and target in step_id_remap:
                transition["target"] = step_id_remap[target]

    return definition


def _derive_workflow_name(description: str) -> str:
    """Generate a meaningful workflow name from the description."""
    desc_lower = description.lower()

    domain_labels: list[str] = []
    label_keywords = [
        (["risk"], "Risk"),
        (["compli", "regulat", "audit"], "Compliance"),
        (["budget", "financ", "cost"], "Financial"),
        (["vendor", "procure", "supplier"], "Procurement"),
        (["resource", "team", "staff"], "Resource"),
        (["quality", "qa", "test"], "Quality"),
        (["schedul", "timeline", "milestone"], "Schedule"),
        (["releas", "deploy", "launch"], "Release"),
        (["change", "cr "], "Change Control"),
        (["portfolio", "strategic"], "Portfolio"),
        (["scope", "requirement", "wbs"], "Scope"),
    ]

    for keywords, label in label_keywords:
        if any(kw in desc_lower for kw in keywords):
            domain_labels.append(label)

    if domain_labels:
        return " & ".join(domain_labels[:3]) + " Workflow"
    return "Generated Workflow"


class NLWorkflowParser:
    """Parse natural language descriptions into workflow definitions using LLM."""

    async def parse(self, description: str) -> dict[str, Any]:
        """Convert a natural language description to a workflow definition via LLM."""
        raw = await _llm_complete(NL_SYSTEM_PROMPT, description)
        if raw:
            parsed = _parse_json_response(raw)
            if parsed and parsed.get("steps"):
                return _sanitise_llm_definition(parsed)

        # Fallback: generate a reasonable workflow from keyword analysis
        return self._keyword_based_parse(description)

    def _keyword_based_parse(self, description: str) -> dict[str, Any]:
        """Analyse description keywords to build a contextual workflow."""
        desc_lower = description.lower()
        steps: list[dict[str, Any]] = []

        # Intake step always first
        next_id = _generate_step_id()
        intake_id = next_id
        steps.append(
            {
                "id": intake_id,
                "type": "task",
                "name": "Intake & Classification",
                "description": "Receive and classify the incoming request",
                "agent_id": "demand-intake-agent",
                "config": {},
                "transitions": [],  # filled in below
            }
        )

        # Detect relevant domain steps from keywords
        matched_steps: list[dict[str, Any]] = []
        for entry in _KEYWORD_AGENT_MAP:
            if any(kw in desc_lower for kw in entry["keywords"]):
                step_id = _generate_step_id()
                step: dict[str, Any] = {
                    "id": step_id,
                    "type": entry["type"],
                    "name": entry["name"],
                    "description": entry["description"],
                    "config": entry.get("config", {}),
                    "transitions": [],
                }
                if entry.get("agent_id"):
                    step["agent_id"] = entry["agent_id"]
                matched_steps.append(step)

        # If no keywords matched, add a generic execution step
        if not matched_steps:
            exec_id = _generate_step_id()
            matched_steps.append(
                {
                    "id": exec_id,
                    "type": "task",
                    "name": "Execute & Deliver",
                    "description": "Execute the planned work",
                    "agent_id": "schedule-planning-agent",
                    "config": {},
                    "transitions": [],
                }
            )

        # Notification step always last
        notify_id = _generate_step_id()
        notify_step: dict[str, Any] = {
            "id": notify_id,
            "type": "notification",
            "name": "Stakeholder Update",
            "description": "Notify stakeholders of completion",
            "agent_id": "stakeholder-communications-agent",
            "config": {},
            "transitions": [],
        }

        # Wire transitions: intake → matched[0] → matched[1] → ... → notify
        all_steps = [steps[0], *matched_steps, notify_step]
        for i, s in enumerate(all_steps[:-1]):
            next_step = all_steps[i + 1]
            if s.get("type") == "decision":
                # Decision steps get conditional branches
                if i + 2 < len(all_steps):
                    s["transitions"] = [
                        {"target": next_step["id"], "condition": "requires_attention == true"},
                        {
                            "target": all_steps[i + 2]["id"],
                            "condition": "requires_attention != true",
                        },
                    ]
                else:
                    s["transitions"] = [{"target": next_step["id"]}]
            else:
                s["transitions"] = [{"target": next_step["id"]}]

        return {
            "name": _derive_workflow_name(description),
            "description": description,
            "steps": all_steps,
        }

    def validate_generated(self, definition: dict[str, Any]) -> dict[str, Any]:
        """Validate a workflow definition for structural and semantic correctness."""
        errors: list[str] = []
        if not definition.get("name"):
            errors.append("Workflow must have a name")
        steps = definition.get("steps", [])
        if not steps:
            errors.append("Workflow must have at least one step")

        valid_types = {"task", "decision", "approval", "notification", "parallel", "api"}
        step_ids = {s.get("id") for s in steps}

        for step in steps:
            step_id = step.get("id", "<unnamed>")

            # Validate step type
            step_type = step.get("type")
            if step_type and step_type not in valid_types:
                errors.append(f"Step {step_id} has invalid type '{step_type}'")

            # Validate agent_id against catalog
            agent_id = step.get("agent_id")
            if agent_id and agent_id not in VALID_AGENT_IDS:
                resolved = _normalize_agent_id(agent_id)
                if resolved:
                    errors.append(
                        f"Step {step_id} uses shorthand agent_id '{agent_id}'; "
                        f"use canonical ID '{resolved}'"
                    )
                else:
                    errors.append(f"Step {step_id} references unknown agent_id '{agent_id}'")

            # Validate transitions reference existing steps
            for t in step.get("transitions", []):
                target = t.get("target")
                if target and target not in step_ids:
                    errors.append(f"Step {step_id} references unknown target '{target}'")

            # Decision steps should have conditions on transitions
            if step_type == "decision":
                transitions = step.get("transitions", [])
                if len(transitions) < 2:
                    errors.append(f"Decision step {step_id} should have at least 2 transitions")

        return {"valid": len(errors) == 0, "errors": errors}

    async def refine(self, definition: dict[str, Any], feedback: str) -> dict[str, Any]:
        """Refine an existing definition based on user feedback via LLM."""
        prompt = REFINE_PROMPT.format(
            current_definition=json.dumps(definition, indent=2),
            feedback=feedback,
        )
        raw = await _llm_complete(NL_SYSTEM_PROMPT, prompt)
        if raw:
            parsed = _parse_json_response(raw)
            if parsed and parsed.get("steps"):
                return _sanitise_llm_definition(parsed)
        # If LLM fails, return original unchanged
        return definition
