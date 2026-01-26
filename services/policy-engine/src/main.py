from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from policy_config import DEFAULT_POLICY_BUNDLE_PATH

logger = logging.getLogger("policy-engine")
logging.basicConfig(level=logging.INFO)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "policy-engine"


class PolicyEvaluationRequest(BaseModel):
    bundle: dict[str, Any] = Field(..., description="Policy bundle to evaluate")


class PolicyEvaluationResponse(BaseModel):
    decision: str
    reasons: list[str]


app = FastAPI(title="Policy Engine", version="0.1.0")


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()


def _load_default_policies() -> dict[str, Any]:
    bundle_path = Path(os.getenv("POLICY_BUNDLE_PATH", str(DEFAULT_POLICY_BUNDLE_PATH)))
    return yaml.safe_load(bundle_path.read_text())


def _get_field(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _apply_rule(bundle: dict[str, Any], rule: dict[str, Any]) -> bool:
    value = _get_field(bundle, rule.get("field", ""))
    operator = rule.get("operator")
    expected = rule.get("value")
    if operator == "contains":
        return expected in str(value or "")
    if operator == "not_contains":
        return expected not in str(value or "")
    return False


def _evaluate(bundle: dict[str, Any], policy_bundle: dict[str, Any]) -> PolicyEvaluationResponse:
    reasons: list[str] = []
    decision = "allow"
    policies = policy_bundle.get("policies", [])

    for policy in policies:
        rules = policy.get("rules", [])
        for rule in rules:
            if not _apply_rule(bundle, rule):
                message = f"{policy.get('id')}: {policy.get('name')}"
                reasons.append(message)
                if policy.get("enforcement") == "blocking":
                    decision = "deny"

    return PolicyEvaluationResponse(decision=decision, reasons=reasons)


@app.post("/policies/evaluate", response_model=PolicyEvaluationResponse)
async def evaluate_policies(request: PolicyEvaluationRequest) -> PolicyEvaluationResponse:
    if not request.bundle.get("metadata"):
        raise HTTPException(status_code=422, detail="Bundle metadata is required")

    policy_bundle = _load_default_policies()
    response = _evaluate(request.bundle, policy_bundle)
    logger.info("policy_evaluated", extra={"decision": response.decision})
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
