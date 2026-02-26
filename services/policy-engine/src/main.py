from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import yaml
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from jsonschema import Draft202012Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parents[3]
_common_src = REPO_ROOT / "packages" / "common" / "src"
if str(_common_src) not in sys.path:
    sys.path.insert(0, str(_common_src))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402
ensure_monorepo_paths(REPO_ROOT)

from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from policy_config import DEFAULT_POLICY_BUNDLE_PATH  # noqa: E402
from security.api_governance import (  # noqa: E402
    apply_api_governance,
    version_response_payload,
)
from security.auth import AuthTenantMiddleware  # noqa: E402

from agents.runtime.src.policy import evaluate_compliance_controls  # noqa: E402
from packages.version import API_VERSION  # noqa: E402
from security.config import load_yaml  # noqa: E402

logger = logging.getLogger("policy-engine")
logging.basicConfig(level=logging.INFO)
SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "policies" / "schema" / "policy-bundle.schema.json"
)


class HealthResponse(BaseModel):
    status: str
    checks: dict[str, dict[str, str]] = Field(default_factory=dict)
    severity: str
    remediation_hint: str
    observed_at: str
    degraded_since: str | None = None
    recovered_at: str | None = None


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


class ComplianceEvaluationRequest(BaseModel):
    payload: dict[str, Any]
    required_fields: list[str] | None = None


class ComplianceEvaluationResponse(BaseModel):
    decision: str
    reasons: list[str]
    sanitized_payload: dict[str, Any]
    masked_fields: list[str]


app = FastAPI(title="Policy Engine", version=API_VERSION, openapi_prefix="/v1")
api_router = APIRouter(prefix="/v1")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz", "/version"})
configure_tracing("policy-engine")
configure_metrics("policy-engine")
app.add_middleware(TraceMiddleware, service_name="policy-engine")
app.add_middleware(RequestMetricsMiddleware, service_name="policy-engine")
apply_api_governance(app, service_name="policy-engine")
meter = configure_metrics("policy-engine")
READINESS_DEGRADED_TOTAL = meter.create_counter(
    name="service_readiness_degraded_total",
    description="Total number of readiness degradation transitions.",
    unit="1",
)
READINESS_RECOVERY_TOTAL = meter.create_counter(
    name="service_readiness_recovered_total",
    description="Total number of readiness recovery transitions.",
    unit="1",
)
READINESS_MTTR_SECONDS = meter.create_histogram(
    name="service_readiness_mttr_seconds",
    description="Readiness mean-time-to-recovery samples in seconds.",
    unit="s",
)
app.state.readiness_state = {
    "last_status": "ok",
    "degraded_since": None,
    "recovered_at": None,
}


@app.on_event("startup")
async def register_policy_schema() -> None:
    data_service_url = os.getenv("DATA_SERVICE_URL")
    if not data_service_url:
        return
    schema = load_yaml(SCHEMA_PATH)
    payload = {"name": "policy-bundle", "schema": schema}
    tenant_id = os.getenv("DATA_SERVICE_TENANT_ID", "system")
    try:
        async with httpx.AsyncClient(base_url=data_service_url.rstrip("/"), timeout=10.0) as client:
            response = await client.post(
                "/v1/schemas", json=payload, headers={"X-Tenant-ID": tenant_id}
            )
            if response.status_code not in {200, 409}:
                response.raise_for_status()
        logger.info("policy_schema_registered", extra={"status_code": response.status_code})
    except httpx.HTTPError as exc:
        logger.warning("policy_schema_registration_failed", extra={"error": str(exc)})


def _observed_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_check(status: str, severity: str, remediation_hint: str) -> dict[str, str]:
    return {
        "status": status,
        "severity": severity,
        "remediation_hint": remediation_hint,
        "observed_at": _observed_at(),
    }


def _sample_policy_evaluation_probe() -> None:
    bundle = _load_default_policies()
    sample_input = {"metadata": {"owner": "healthcheck", "name": "probe"}}
    _evaluate(sample_input, bundle)


async def _check_data_service_reachability() -> dict[str, str]:
    data_service_url = os.getenv("DATA_SERVICE_URL")
    if not data_service_url:
        return _build_check(
            "ok", "info", "No DATA_SERVICE_URL configured; external reachability optional."
        )
    if os.getenv("POLICY_ENGINE_REQUIRE_DATA_SERVICE", "false").lower() not in {"1", "true", "yes"}:
        return _build_check(
            "ok",
            "info",
            "Data service check is optional unless POLICY_ENGINE_REQUIRE_DATA_SERVICE=true.",
        )
    try:
        async with httpx.AsyncClient(base_url=data_service_url.rstrip("/"), timeout=5.0) as client:
            response = await client.get("/readyz")
            response.raise_for_status()
        return _build_check("ok", "info", "")
    except httpx.HTTPError:
        return _build_check(
            "down",
            "critical",
            "Verify DATA_SERVICE_URL connectivity and restore data-service readiness.",
        )


def _update_readiness_metrics(status: str) -> tuple[str | None, str | None]:
    state = app.state.readiness_state
    previous = state["last_status"]
    now = datetime.now(timezone.utc)
    if status != "ok" and previous == "ok":
        state["degraded_since"] = now
        READINESS_DEGRADED_TOTAL.add(1, {"service.name": "policy-engine"})
    if status == "ok" and previous != "ok":
        degraded_since = state.get("degraded_since")
        if degraded_since:
            READINESS_MTTR_SECONDS.record(
                (now - degraded_since).total_seconds(), {"service.name": "policy-engine"}
            )
        state["recovered_at"] = now
        state["degraded_since"] = None
        READINESS_RECOVERY_TOTAL.add(1, {"service.name": "policy-engine"})
    state["last_status"] = status
    degraded_since = state.get("degraded_since")
    recovered_at = state.get("recovered_at")
    return (
        degraded_since.isoformat() if degraded_since else None,
        recovered_at.isoformat() if recovered_at else None,
    )


def _to_response(checks: dict[str, dict[str, str]], status_code: int) -> JSONResponse:
    has_critical = any(item["severity"] == "critical" for item in checks.values())
    status = "ok" if all(item["status"] == "ok" for item in checks.values()) else "degraded"
    severity = "info" if status == "ok" else ("critical" if has_critical else "warning")
    remediation_hint = "; ".join(
        sorted({item["remediation_hint"] for item in checks.values() if item["remediation_hint"]})
    )
    degraded_since, recovered_at = _update_readiness_metrics(status)
    payload = HealthResponse(
        status=status,
        checks=checks,
        severity=severity,
        remediation_hint=remediation_hint,
        observed_at=_observed_at(),
        degraded_since=degraded_since,
        recovered_at=recovered_at,
    )
    return JSONResponse(
        status_code=status_code if status != "ok" else 200, content=payload.model_dump()
    )


@app.get("/livez", response_model=HealthResponse)
async def livez() -> HealthResponse:
    checks = {"process": _build_check("ok", "info", "")}
    return HealthResponse(
        status="ok",
        checks=checks,
        severity="info",
        remediation_hint="",
        observed_at=_observed_at(),
    )


@app.get("/readyz", response_model=HealthResponse)
async def readyz() -> JSONResponse:
    checks = {
        "policy_bundle_load_parse": _build_check("ok", "info", ""),
        "rbac_config": _build_check("ok", "info", ""),
    }
    try:
        _load_default_policies()
    except (HTTPException, OSError, ValueError, yaml.YAMLError):
        checks["policy_bundle_load_parse"] = _build_check(
            "down", "critical", "Restore default policy bundle and ensure it conforms to schema."
        )
    try:
        _load_rbac_config()
    except (OSError, ValueError, yaml.YAMLError):
        checks["rbac_config"] = _build_check(
            "down", "warning", "Restore RBAC roles/permissions/field-level configuration files."
        )
    checks["data_service_reachability"] = await _check_data_service_reachability()
    return _to_response(checks, status_code=503)


@app.get("/readyz/deep", response_model=HealthResponse)
async def deep_readyz() -> JSONResponse:
    checks = {"policy_sample_evaluation": _build_check("ok", "info", "")}
    try:
        _sample_policy_evaluation_probe()
    except Exception:  # pragma: no cover - defensive guard for deep probe failures
        checks["policy_sample_evaluation"] = _build_check(
            "down", "critical", "Fix policy parsing/evaluation path so sample probe can execute."
        )
    return _to_response(checks, status_code=503)


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> JSONResponse:
    return await readyz()


@app.get("/version")
async def version() -> dict[str, str]:
    return version_response_payload("policy-engine")


def _load_default_policies() -> dict[str, Any]:
    bundle_path = Path(os.getenv("POLICY_BUNDLE_PATH", str(DEFAULT_POLICY_BUNDLE_PATH)))
    data = load_yaml(bundle_path)
    _validate_bundle(data)
    return data


def _validate_bundle(bundle: dict[str, Any]) -> None:
    schema = load_yaml(SCHEMA_PATH)
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
        load_yaml(roles_path),
        load_yaml(permissions_path),
        load_yaml(field_path),
    )


def _load_abac_config() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[3]
    policy_path = Path(
        os.getenv("ABAC_POLICY_PATH", repo_root / "config" / "abac" / "policies.yaml")
    )
    if not policy_path.exists():
        return {"policies": [], "default_decision": "allow"}
    return load_yaml(policy_path)


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


@api_router.post("/policies/evaluate", response_model=PolicyEvaluationResponse)
async def evaluate_policies(request: PolicyEvaluationRequest) -> PolicyEvaluationResponse:
    if not request.bundle.get("metadata"):
        raise HTTPException(status_code=422, detail="Bundle metadata is required")

    _validate_bundle(request.bundle)
    policy_bundle = _load_default_policies()
    response = _evaluate(request.bundle, policy_bundle)
    logger.info("policy_evaluated", extra={"decision": response.decision})
    return response


@api_router.post("/rbac/evaluate", response_model=RBACEvaluationResponse)
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


@api_router.post("/compliance/evaluate", response_model=ComplianceEvaluationResponse)
async def evaluate_compliance(request: ComplianceEvaluationRequest) -> ComplianceEvaluationResponse:
    decision = evaluate_compliance_controls(
        request.payload,
        required_fields=set(request.required_fields) if request.required_fields else None,
    )
    logger.info(
        "compliance_evaluated",
        extra={"decision": decision.decision, "masked_fields": list(decision.masked_fields)},
    )
    return ComplianceEvaluationResponse(
        decision=decision.decision,
        reasons=list(decision.reasons),
        sanitized_payload=decision.sanitized_payload,
        masked_fields=list(decision.masked_fields),
    )


@api_router.post("/abac/evaluate", response_model=ABACEvaluationResponse)
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


app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
