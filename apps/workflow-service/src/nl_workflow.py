"""Natural language to workflow definition parser.

Uses LLM to convert natural language descriptions into structured workflow
definitions, with validation and iterative refinement.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("workflow.nl_workflow")

NL_SYSTEM_PROMPT = """You are a workflow definition generator for a Project Portfolio Management system.
Convert the user's natural language description into a structured workflow definition.

Output valid JSON with this schema:
{
  "name": "string",
  "description": "string",
  "steps": [
    {
      "id": "string",
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

Available agents: intent-router, demand-intake, business-case, portfolio-optimisation,
program-management, scope-definition, lifecycle-governance, schedule-planning,
resource-management, financial-management, vendor-procurement, quality-management,
risk-management, compliance-governance, change-control, release-deployment,
knowledge-management, continuous-improvement, stakeholder-communications,
analytics-insights, data-synchronisation, system-health, workflow-engine.

Return ONLY the JSON, no markdown formatting."""

REFINE_PROMPT = """The user wants to modify this existing workflow definition.
Current definition:
{current_definition}

User feedback: {feedback}

Output the updated workflow definition as valid JSON. Return ONLY the JSON."""


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


class NLWorkflowParser:
    """Parse natural language descriptions into workflow definitions using LLM."""

    async def parse(self, description: str) -> dict[str, Any]:
        """Convert a natural language description to a workflow definition via LLM."""
        raw = await _llm_complete(NL_SYSTEM_PROMPT, description)
        if raw:
            parsed = _parse_json_response(raw)
            if parsed and parsed.get("steps"):
                return parsed

        # Fallback: generate a reasonable workflow from keyword analysis
        return self._keyword_based_parse(description)

    def _keyword_based_parse(self, description: str) -> dict[str, Any]:
        """Analyze description keywords to build a contextual workflow."""
        desc_lower = description.lower()
        steps: list[dict[str, Any]] = []
        step_counter = 1

        # Intake step always first
        steps.append({
            "id": f"step-{step_counter}",
            "type": "task",
            "name": "Intake & Classification",
            "description": "Receive and classify the incoming request",
            "agent_id": "demand-intake",
            "config": {},
            "transitions": [{"target": f"step-{step_counter + 1}"}],
        })
        step_counter += 1

        # Conditional steps based on description content
        if any(kw in desc_lower for kw in ["risk", "assess", "evaluate", "review"]):
            steps.append({
                "id": f"step-{step_counter}",
                "type": "decision",
                "name": "Risk Assessment Gate",
                "description": "Evaluate risk level based on the request characteristics",
                "agent_id": "risk-management",
                "config": {},
                "transitions": [
                    {"target": f"step-{step_counter + 1}", "condition": "risk_level == 'high'"},
                    {"target": f"step-{step_counter + 2}", "condition": "risk_level != 'high'"},
                ],
            })
            step_counter += 1

        if any(kw in desc_lower for kw in ["approv", "sign-off", "authorize", "cfo", "executive"]):
            steps.append({
                "id": f"step-{step_counter}",
                "type": "approval",
                "name": "Executive Approval",
                "description": "Requires executive sign-off before proceeding",
                "config": {"approver_role": "executive"},
                "transitions": [{"target": f"step-{step_counter + 1}"}],
            })
            step_counter += 1

        if any(kw in desc_lower for kw in ["budget", "cost", "financ", "spend"]):
            steps.append({
                "id": f"step-{step_counter}",
                "type": "task",
                "name": "Financial Review",
                "description": "Review budget implications and cost estimates",
                "agent_id": "financial-management",
                "config": {},
                "transitions": [{"target": f"step-{step_counter + 1}"}],
            })
            step_counter += 1

        if any(kw in desc_lower for kw in ["compli", "regulat", "audit", "gdpr", "sox"]):
            steps.append({
                "id": f"step-{step_counter}",
                "type": "task",
                "name": "Compliance Check",
                "description": "Verify regulatory compliance requirements",
                "agent_id": "compliance-governance",
                "config": {},
                "transitions": [{"target": f"step-{step_counter + 1}"}],
            })
            step_counter += 1

        # Execution step
        steps.append({
            "id": f"step-{step_counter}",
            "type": "task",
            "name": "Execute & Deliver",
            "description": "Execute the planned work",
            "agent_id": "schedule-planning",
            "config": {},
            "transitions": [{"target": f"step-{step_counter + 1}"}],
        })
        step_counter += 1

        # Notification step always last
        steps.append({
            "id": f"step-{step_counter}",
            "type": "notification",
            "name": "Stakeholder Update",
            "description": "Notify stakeholders of completion",
            "agent_id": "stakeholder-communications",
            "config": {},
            "transitions": [],
        })

        return {
            "name": "Generated Workflow",
            "description": description,
            "steps": steps,
        }

    def validate_generated(self, definition: dict[str, Any]) -> dict[str, Any]:
        errors: list[str] = []
        if not definition.get("name"):
            errors.append("Workflow must have a name")
        steps = definition.get("steps", [])
        if not steps:
            errors.append("Workflow must have at least one step")
        step_ids = {s.get("id") for s in steps}
        for step in steps:
            for t in step.get("transitions", []):
                if t.get("target") and t["target"] not in step_ids:
                    errors.append(f"Step {step.get('id')} references unknown target {t['target']}")
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
                return parsed
        # If LLM fails, return original unchanged
        return definition
