from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

import yaml
import httpx
from fastapi import FastAPI, HTTPException
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for root in (SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from policy_config import DEFAULT_POLICY_BUNDLE_PATH  # noqa: E402
from security.auth import AuthTenantMiddleware  # noqa: E402

logger = logging.getLogger("policy-engine")
logging.basicConfig(level=logging.INFO)
SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "policies" / "schema" / "policy-bundle.schema.json"
)


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


class ABACEvaluationRequest(BaseModel):
    tenant_id: str
    subject: dict[str, Any]
    action: str
    resource: dict[str, Any] | None = None
    context: dict[str, Any] | None = None


class ABACEvaluationResponse(BaseModel):
    decision: str
    reasons: list[str]


app = FastAPI(title="Policy Engine", version="0.1.0")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz"})
configure_tracing("policy-engine")
configure_metrics("policy-engine")
app.add_middleware(TraceMiddleware, service_name="policy-engine")
app.add_middleware(RequestMetricsMiddleware, service_name="policy-engine")


@app.on_event("startup")
async def register_policy_schema() -> None:
    data_service_url = os.getenv("DATA_SERVICE_URL")
    if not data_service_url:
        return
    schema = yaml.safe_load(SCHEMA_PATH.read_text())
    payload = {"name": "policy-bundle", "schema": schema}
    tenant_id = os.getenv("DATA_SERVICE_TENANT_ID", "system")
    try:
        async with httpx.AsyncClient(base_url=data_service_url.rstrip("/"), timeout=10.0) as client:
            response = await client.post(
                "/schemas", json=payload, headers={"X-Tenant-ID": tenant_id}
            )
            if response.status_code not in {200, 409}:
                response.raise_for_status()
        logger.info("policy_schema_registered", extra={"status_code": response.status_code})
    except httpx.HTTPError as exc:
        logger.warning("policy_schema_registration_failed", extra={"error": str(exc)})


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()


def _load_default_policies() -> dict[str, Any]:
    bundle_path = Path(os.getenv("POLICY_BUNDLE_PATH", str(DEFAULT_POLICY_BUNDLE_PATH)))
    data = yaml.safe_load(bundle_path.read_text())
    _validate_bundle(data)
    return data


def _validate_bundle(bundle: dict[str, Any]) -> None:
    schema = yaml.safe_load(SCHEMA_PATH.read_text())
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(bundle), key=lambda err: err.path)
    if errors:
        formatted = "; ".join(error.message for error in errors)
        raise HTTPException(status_code=422, detail=f"Policy bundle validation failed: {formatted}")


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


def _load_abac_config() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[3]
    policy_path = Path(os.getenv("ABAC_POLICY_PATH", repo_root / "config" / "abac" / "policies.yaml"))
    if not policy_path.exists():
        return {"policies": [], "default_decision": "allow"}
    return yaml.safe_load(policy_path.read_text())


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
    if operator == "equals":
        return value == expected
    if operator == "not_equals":
        return value != expected
    if operator == "contains":
        if isinstance(value, list):
            return expected in value
        return expected in str(value or "")
    if operator == "not_contains":
        if isinstance(value, list):
            return expected not in value
        return expected not in str(value or "")
    if operator == "gte":
        return value is not None and expected is not None and value >= expected
    if operator == "lte":
        return value is not None and expected is not None and value <= expected
    if operator == "in":
        return value in (expected or [])
    if operator == "not_in":
        return value not in (expected or [])
    return False


def _apply_abac_rule(payload: dict[str, Any], rule: dict[str, Any]) -> bool:
    value = _get_field(payload, rule.get("field", ""))
    expected = rule.get("value")
    value_from = rule.get("value_from")
    if value_from:
        expected = _get_field(payload, value_from)
    operator = rule.get("operator")
    if operator == "equals":
        return value == expected
    if operator == "not_equals":
        return value != expected
    if operator == "contains":
        if isinstance(value, list):
            return expected in value
        return expected in str(value or "")
    if operator == "not_contains":
        if isinstance(value, list):
            return expected not in value
        return expected not in str(value or "")
    if operator == "gte":
        return value is not None and expected is not None and value >= expected
    if operator == "lte":
        return value is not None and expected is not None and value <= expected
    if operator == "in":
        return value in (expected or [])
    if operator == "not_in":
        return value not in (expected or [])
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


def _evaluate_abac(
    request_payload: dict[str, Any], policy_cfg: dict[str, Any]
) -> ABACEvaluationResponse:
    reasons: list[str] = []
    allow_match = False
    default_decision = policy_cfg.get("default_decision", "allow")

    for policy in policy_cfg.get("policies", []):
        rules = policy.get("rules", [])
        if not rules:
            continue
        if all(_apply_abac_rule(request_payload, rule) for rule in rules):
            reasons.append(f"{policy.get('id')}: {policy.get('name')}")
            if policy.get("effect") == "deny":
                return ABACEvaluationResponse(decision="deny", reasons=reasons)
            allow_match = True

    if allow_match:
        return ABACEvaluationResponse(decision="allow", reasons=reasons)
    return ABACEvaluationResponse(decision=default_decision, reasons=reasons)

@app.post("/policies/evaluate", response_model=PolicyEvaluationResponse)
async def evaluate_policies(request: PolicyEvaluationRequest) -> PolicyEvaluationResponse:
    if not request.bundle.get("metadata"):
        raise HTTPException(status_code=422, detail="Bundle metadata is required")

    _validate_bundle(request.bundle)
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


@app.post("/abac/evaluate", response_model=ABACEvaluationResponse)
async def evaluate_abac(request: ABACEvaluationRequest) -> ABACEvaluationResponse:
    policy_cfg = _load_abac_config()
    payload = {
        "subject": request.subject,
        "resource": request.resource or {},
        "context": request.context or {},
        "action": request.action,
    }
    response = _evaluate_abac(payload, policy_cfg)
    logger.info("abac_evaluated", extra={"decision": response.decision, "action": request.action})
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
