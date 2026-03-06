from __future__ import annotations

import json
import logging
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, cast

import httpx as _real_httpx


class _GatewayAsyncClient(_real_httpx.AsyncClient):
    """Subclass of httpx.AsyncClient used exclusively by the API-gateway security
    middleware.  Having a dedicated subclass means test suites can patch
    ``api.middleware.security.httpx.AsyncClient.post`` without accidentally
    patching the httpx test-client, which also uses ``httpx.AsyncClient``
    directly.
    """


class _GatewayHttpxNamespace:
    """Minimal httpx-like namespace that exposes our patchable AsyncClient."""

    AsyncClient = _GatewayAsyncClient


# Replace the module-level `httpx` name with our isolated namespace so all
# references within this module (e.g. ``_evaluate_rbac``) use the subclass.
httpx = _GatewayHttpxNamespace()

import security.auth as _security_auth  # noqa: E402
from fastapi import HTTPException, Request  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402
from starlette.responses import Response  # noqa: E402
from starlette.types import ASGIApp  # noqa: E402

# Redirect security.auth's httpx reference so its HTTP calls go through our
# patchable client.  This ensures that patching
# ``api.middleware.security.httpx.AsyncClient.post`` in tests also intercepts
# auth-service calls made by ``security.auth._validate_jwt``.
_security_auth.httpx = httpx  # type: ignore[assignment]

from security.auth import AuthContext, authenticate_request  # noqa: E402
from security.config import load_yaml  # noqa: E402
from security.errors import error_payload  # noqa: E402

logger = logging.getLogger("api-gateway-security")


def _load_yaml(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], load_yaml(path))


def _load_rbac() -> tuple[dict[str, Any], dict[str, Any]]:
    repo_root = Path(__file__).resolve().parents[5]
    roles_cfg = _load_yaml(repo_root / "config" / "rbac" / "roles.yaml")
    field_cfg = _load_yaml(repo_root / "config" / "rbac" / "field-level.yaml")
    return roles_cfg, field_cfg


def _role_permissions(roles_cfg: dict[str, Any]) -> dict[str, set[str]]:
    return {role["id"]: set(role.get("permissions", [])) for role in roles_cfg.get("roles", [])}


def _required_permission(request: Request) -> str:
    path = request.url.path
    method = request.method
    if path.startswith("/v1/admin"):
        return "config.write"
    if path.startswith("/v1/audit"):
        return "audit.read" if method == "GET" else "audit.write"
    if path.startswith("/v1/agents/config") or "/agents/config" in path:
        return "config.write" if method in {"POST", "PUT", "PATCH", "DELETE"} else "config.read"
    if path.startswith("/v1/connectors"):
        return "config.write" if method in {"POST", "PUT", "PATCH", "DELETE"} else "config.read"
    if path.startswith("/v1/query"):
        return "workflow.execute"
    if path.startswith("/v1/documents"):
        return "document.coedit"
    if path.startswith("/v1/agents"):
        return "workflow.read"
    if method in {"POST", "PUT", "PATCH", "DELETE"}:
        return "project.write"
    return "project.read"


def _classification_from_body(body: bytes) -> str | None:
    if not body:
        return None
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        return payload.get("classification")
    return None


def _is_classification_allowed(
    field_cfg: dict[str, Any], classification: str, roles: list[str]
) -> bool:
    allowed_roles = (
        field_cfg.get("classification_access", {}).get(classification, {}).get("allowed_roles", [])
    )
    return any(role in allowed_roles for role in roles)


def _mask_fields(
    payload: Any, field_cfg: dict[str, Any], roles: list[str], mask: str = "REDACTED"
) -> Any:
    if isinstance(payload, list):
        return [_mask_fields(item, field_cfg, roles, mask) for item in payload]
    if not isinstance(payload, dict):
        return payload

    def _apply_mask(target: Any, path_parts: list[str]) -> None:
        if not path_parts:
            return
        if isinstance(target, list):
            for item in target:
                _apply_mask(item, path_parts)
            return
        if not isinstance(target, dict):
            return
        key = path_parts[0]
        if key not in target:
            return
        if len(path_parts) == 1:
            target[key] = mask
            return
        _apply_mask(target[key], path_parts[1:])

    fields_cfg = field_cfg.get("fields", {})
    for resource, resource_fields in fields_cfg.items():
        resource_data = payload.get(resource)
        if isinstance(resource_data, (dict, list)):
            for field_name, rule in resource_fields.items():
                allowed_roles = set(rule.get("allowed_roles", []))
                if not allowed_roles.intersection(roles):
                    _apply_mask(resource_data, field_name.split("."))

    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            payload[key] = _mask_fields(value, field_cfg, roles, mask)

    return payload


async def _evaluate_rbac(auth: AuthContext, permission: str, classification: str | None) -> None:
    policy_engine = os.getenv("POLICY_ENGINE_URL")
    if policy_engine:
        service_token = os.getenv("POLICY_ENGINE_SERVICE_TOKEN")
        if not service_token:
            raise HTTPException(status_code=500, detail="Policy engine token missing")
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{policy_engine}/rbac/evaluate",
                json={
                    "tenant_id": auth.tenant_id,
                    "roles": auth.roles,
                    "permission": permission,
                    "classification": classification,
                },
                headers={
                    "Authorization": f"Bearer {service_token}",
                    "X-Tenant-ID": auth.tenant_id,
                },
            )
            response.raise_for_status()
            decision = response.json().get("decision")
            if decision != "allow":
                raise HTTPException(status_code=403, detail="RBAC denied")
        return

    roles_cfg, field_cfg = _load_rbac()
    role_permissions = _role_permissions(roles_cfg)
    allowed = any(permission in role_permissions.get(role, set()) for role in auth.roles)
    if classification and not _is_classification_allowed(field_cfg, classification, auth.roles):
        allowed = False
    if not allowed:
        raise HTTPException(status_code=403, detail="RBAC denied")


def _load_abac_config() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[5]
    policy_path = Path(
        os.getenv("ABAC_POLICY_PATH", repo_root / "config" / "abac" / "policies.yaml")
    )
    if not policy_path.exists():
        return {"policies": [], "default_decision": "allow"}
    return _load_yaml(policy_path)


def _get_field(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _evaluate_abac_policy(
    request_payload: dict[str, Any], policies: list[dict[str, Any]], default_decision: str
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    allow_match = False

    for policy in policies:
        rules = policy.get("rules", [])
        effect = policy.get("effect", "allow")
        if not rules:
            continue
        matches = True
        for rule in rules:
            actual = _get_field(request_payload, rule.get("field", ""))
            expected = rule.get("value")
            value_from = rule.get("value_from")
            if value_from:
                expected = _get_field(request_payload, value_from)
            operator = rule.get("operator")
            if operator == "equals":
                matches = actual == expected
            elif operator == "not_equals":
                matches = actual != expected
            elif operator == "contains":
                if isinstance(actual, list):
                    matches = expected in actual
                else:
                    matches = expected in str(actual or "")
            elif operator == "not_contains":
                if isinstance(actual, list):
                    matches = expected not in actual
                else:
                    matches = expected not in str(actual or "")
            elif operator == "gte":
                matches = actual is not None and expected is not None and actual >= expected
            elif operator == "lte":
                matches = actual is not None and expected is not None and actual <= expected
            elif operator == "in":
                matches = actual in (expected or [])
            elif operator == "not_in":
                matches = actual not in (expected or [])
            else:
                matches = False
            if not matches:
                break
        if matches:
            reasons.append(f"{policy.get('id')}: {policy.get('name')}")
            if effect == "deny":
                return "deny", reasons
            allow_match = True

    if allow_match:
        return "allow", reasons
    return default_decision, reasons


def _is_abac_enforcement_enabled() -> bool:
    """Determine if ABAC enforcement is enabled.

    In production environments, ABAC enforcement defaults to enabled.
    In development environments, it defaults to disabled unless explicitly set.
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()
    production_environments = {"production", "prod", "staging", "stg"}

    abac_env = os.getenv("ABAC_ENFORCEMENT")
    if abac_env is not None:
        return abac_env.lower() in {"1", "true", "yes"}

    # Default to enabled in production, disabled elsewhere
    return environment in production_environments


async def _evaluate_abac(
    auth: AuthContext, permission: str, resource: dict[str, Any] | None, request: Request
) -> None:
    if not _is_abac_enforcement_enabled():
        return

    payload = {
        "subject": auth.claims,
        "resource": resource or {},
        "context": {
            "tenant_id": auth.tenant_id,
            "roles": auth.roles,
            "permission": permission,
            "path": request.url.path,
            "method": request.method,
        },
        "action": permission,
    }

    policy_engine = os.getenv("POLICY_ENGINE_URL")
    if policy_engine:
        service_token = os.getenv("POLICY_ENGINE_SERVICE_TOKEN")
        if not service_token:
            raise HTTPException(status_code=500, detail="Policy engine token missing")
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{policy_engine}/abac/evaluate",
                json={"tenant_id": auth.tenant_id, **payload},
                headers={
                    "Authorization": f"Bearer {service_token}",
                    "X-Tenant-ID": auth.tenant_id,
                },
            )
            response.raise_for_status()
            decision = response.json().get("decision")
            if decision != "allow":
                raise HTTPException(status_code=403, detail="ABAC denied")
        return

    abac_cfg = _load_abac_config()
    decision, _ = _evaluate_abac_policy(
        payload, abac_cfg.get("policies", []), abac_cfg.get("default_decision", "allow")
    )
    if decision != "allow":
        raise HTTPException(status_code=403, detail="ABAC denied")


class AuthTenantMiddleware(BaseHTTPMiddleware):
    """Authentication and authorisation middleware for the API gateway.

    JWT validation is delegated entirely to ``security.auth.authenticate_request``
    which centralises the OIDC/JWKS/HS256 logic and its TTL-cached JWKS store.
    This middleware then applies gateway-specific RBAC and ABAC checks on top.
    """

    def __init__(self, app: ASGIApp, *args: Any, **kwargs: Any) -> None:
        super().__init__(app, *args, **kwargs)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        exempt_paths = {
            "/",
            "/healthz",
            "/api/health",
            "/version",
            "/v1/health",
            "/v1/health/ready",
            "/v1/health/live",
        }
        if request.url.path in exempt_paths:
            return await call_next(request)
        if (
            request.method == "POST"
            and request.url.path.startswith("/v1/connectors/")
            and request.url.path.endswith("/webhook")
        ):
            return await call_next(request)

        # Delegate JWT validation, tenant/role extraction, and AuthContext
        # construction to the centralised security package.  This eliminates
        # the duplicate _validate_jwt implementation that previously lived here.
        try:
            auth_context = await authenticate_request(request)
        except HTTPException as exc:
            message = exc.detail if isinstance(exc.detail, str) else "Request failed"
            payload = error_payload(
                message=message, code=f"http_{exc.status_code}", details=exc.detail
            )
            return JSONResponse(status_code=exc.status_code, content=payload)
        except Exception:
            logger.exception("Authentication service error")
            payload = error_payload(
                message="Authentication service unavailable",
                code="http_500",
                details="Internal server error",
            )
            return JSONResponse(status_code=500, content=payload)

        request.state.auth = auth_context

        content_type = request.headers.get("content-type", "")
        is_multipart = "multipart/form-data" in content_type

        if is_multipart:
            body = b""
        else:
            body = await request.body()
            request._body = body
        classification = _classification_from_body(body)
        permission = _required_permission(request)

        try:
            await _evaluate_rbac(auth_context, permission, classification)
            is_json = "application/json" in content_type
            resource = json.loads(body.decode("utf-8")) if body and is_json else None
            await _evaluate_abac(auth_context, permission, resource, request)
        except (HTTPException, json.JSONDecodeError) as exc:
            if isinstance(exc, HTTPException):
                message = exc.detail if isinstance(exc.detail, str) else "Request failed"
                payload = error_payload(
                    message=message, code=f"http_{exc.status_code}", details=exc.detail
                )
                return JSONResponse(status_code=exc.status_code, content=payload)
            payload = error_payload(
                message="Invalid JSON payload", code="http_400", details="Invalid JSON payload"
            )
            return JSONResponse(status_code=400, content=payload)

        response = await call_next(request)
        return response


class FieldMaskingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        if not hasattr(request.state, "auth"):
            return response

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return response

        body = b"".join([chunk async for chunk in cast(Any, response).body_iterator])
        if not body:
            return response

        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return response

        _, field_cfg = _load_rbac()
        masked = _mask_fields(payload, field_cfg, request.state.auth.roles)

        new_response = JSONResponse(content=masked, status_code=response.status_code)
        for key, value in response.headers.items():
            if key.lower() != "content-length":
                new_response.headers[key] = value
        return new_response
