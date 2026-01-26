from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
if str(SECURITY_ROOT) not in sys.path:
    sys.path.insert(0, str(SECURITY_ROOT))

from policy_config import DEFAULT_POLICY_BUNDLE_PATH  # noqa: E402
from security.auth import AuthTenantMiddleware  # noqa: E402

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


class RBACEvaluationRequest(BaseModel):
    tenant_id: str
    roles: list[str]
    permission: str
    classification: str | None = None
    resource: dict[str, Any] | None = None


class RBACEvaluationResponse(BaseModel):
    decision: str
    reasons: list[str]


app = FastAPI(title="Policy Engine", version="0.1.0")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz"})


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()


def _load_default_policies() -> dict[str, Any]:
    bundle_path = Path(os.getenv("POLICY_BUNDLE_PATH", str(DEFAULT_POLICY_BUNDLE_PATH)))
    return yaml.safe_load(bundle_path.read_text())


def _load_rbac_config() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    repo_root = Path(__file__).resolve().parents[3]
    roles_path = repo_root / "config" / "rbac" / "roles.yaml"
    permissions_path = repo_root / "config" / "rbac" / "permissions.yaml"
    field_path = repo_root / "config" / "rbac" / "field-level.yaml"
    return (
        yaml.safe_load(roles_path.read_text()),
        yaml.safe_load(permissions_path.read_text()),
        yaml.safe_load(field_path.read_text()),
    )


def _build_role_permissions(roles_cfg: dict[str, Any]) -> dict[str, set[str]]:
    role_permissions: dict[str, set[str]] = {}
    for role in roles_cfg.get("roles", []):
        role_permissions[role["id"]] = set(role.get("permissions", []))
    return role_permissions


def _classification_allowed(
    field_cfg: dict[str, Any], classification: str, roles: list[str]
) -> bool:
    allowed = (
        field_cfg.get("classification_access", {}).get(classification, {}).get("allowed_roles", [])
    )
    return any(role in allowed for role in roles)


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


@app.post("/rbac/evaluate", response_model=RBACEvaluationResponse)
async def evaluate_rbac(request: RBACEvaluationRequest) -> RBACEvaluationResponse:
    roles_cfg, _, field_cfg = _load_rbac_config()
    role_permissions = _build_role_permissions(roles_cfg)

    allowed = False
    reasons: list[str] = []

    for role in request.roles:
        permissions = role_permissions.get(role, set())
        if request.permission in permissions:
            allowed = True
            break
        reasons.append(f"role:{role} lacks {request.permission}")

    if request.classification and not _classification_allowed(
        field_cfg, request.classification, request.roles
    ):
        allowed = False
        reasons.append(f"classification {request.classification} denied for roles {request.roles}")

    decision = "allow" if allowed else "deny"
    logger.info("rbac_evaluated", extra={"decision": decision, "permission": request.permission})
    return RBACEvaluationResponse(decision=decision, reasons=reasons)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
