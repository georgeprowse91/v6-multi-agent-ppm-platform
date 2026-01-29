from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import httpx
import jwt
import yaml
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from jwt import InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("api-gateway-security")


@dataclass
class AuthContext:
    tenant_id: str
    subject: str
    roles: list[str]
    claims: dict[str, Any]


def _load_yaml(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(path.read_text()))


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
    if path.startswith("/api/v1/audit"):
        return "audit.read" if method == "GET" else "audit.write"
    if path.startswith("/api/v1/agents/config") or "/agents/config" in path:
        return "config.write" if method in {"POST", "PUT", "PATCH", "DELETE"} else "config.read"
    if path.startswith("/api/v1/connectors"):
        return "config.write" if method in {"POST", "PUT", "PATCH", "DELETE"} else "config.read"
    if path.startswith("/api/v1/query"):
        return "workflow.execute"
    if path.startswith("/api/v1/agents"):
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


def _get_claim(claims: dict[str, Any], path: str) -> Any:
    current: Any = claims
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


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


_OIDC_CONFIG_CACHE: dict[str, dict[str, Any]] = {}


async def _load_oidc_config(discovery_url: str) -> dict[str, Any]:
    if discovery_url in _OIDC_CONFIG_CACHE:
        return _OIDC_CONFIG_CACHE[discovery_url]
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(discovery_url)
        response.raise_for_status()
        data = response.json()
    _OIDC_CONFIG_CACHE[discovery_url] = data
    return data


async def _validate_jwt(token: str) -> dict[str, Any]:
    identity_url = os.getenv("IDENTITY_ACCESS_URL")
    if identity_url:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(f"{identity_url}/auth/validate", json={"token": token})
            response.raise_for_status()
            data = response.json()
            if not data.get("active"):
                raise HTTPException(status_code=401, detail="Invalid token")
            return data.get("claims") or {}

    jwt_secret = os.getenv("IDENTITY_JWT_SECRET")
    jwks_url = os.getenv("IDENTITY_JWKS_URL")
    discovery_url = os.getenv("IDENTITY_OIDC_DISCOVERY_URL")
    audience = os.getenv("IDENTITY_AUDIENCE")
    issuer = os.getenv("IDENTITY_ISSUER")
    try:
        if not jwks_url and (discovery_url or issuer):
            discovery_endpoint = discovery_url or (
                f"{issuer.rstrip('/')}/.well-known/openid-configuration" if issuer else None
            )
            if discovery_endpoint:
                oidc_config = await _load_oidc_config(discovery_endpoint)
                jwks_url = oidc_config.get("jwks_uri")
                issuer = issuer or oidc_config.get("issuer")
        if jwks_url:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(jwks_url)
                response.raise_for_status()
                jwks = response.json()
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
            if not key:
                raise HTTPException(status_code=401, detail="Invalid token key")
            public_key = cast(RSAPublicKey, jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key)))
            return cast(
                dict[str, Any],
                jwt.decode(
                    token,
                    public_key,
                    algorithms=[unverified_header.get("alg", "RS256")],
                    audience=audience,
                    issuer=issuer,
                    options={"verify_aud": bool(audience), "verify_iss": bool(issuer)},
                ),
            )
        if not jwt_secret:
            raise HTTPException(status_code=500, detail="JWT validation configuration missing")
        return cast(
            dict[str, Any],
            jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                audience=audience,
                issuer=issuer,
                options={"verify_aud": bool(audience), "verify_iss": bool(issuer)},
            ),
        )
    except InvalidTokenError as exc:
        logger.warning("token_validation_failed", extra={"error": str(exc)})
        raise HTTPException(status_code=401, detail="Invalid token") from exc


def _dev_claims_from_jwt(token: str) -> dict[str, Any] | None:
    dev_secret = os.getenv("AUTH_DEV_JWT_SECRET")
    if not dev_secret:
        return None
    try:
        return cast(
            dict[str, Any],
            jwt.decode(
                token,
                dev_secret,
                algorithms=["HS256"],
                options={"verify_aud": False, "verify_iss": False},
            ),
        )
    except InvalidTokenError as exc:
        logger.warning("dev_token_validation_failed", extra={"error": str(exc)})
        return None


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
    policy_path = Path(os.getenv("ABAC_POLICY_PATH", repo_root / "config" / "abac" / "policies.yaml"))
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


async def _evaluate_abac(
    auth: AuthContext, permission: str, resource: dict[str, Any] | None, request: Request
) -> None:
    if os.getenv("ABAC_ENFORCEMENT", "false").lower() not in {"1", "true", "yes"}:
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
    async def dispatch(self, request: Request, call_next):
        exempt_paths = {
            "/",
            "/healthz",
            "/version",
            "/api/v1/health",
            "/api/v1/health/ready",
            "/api/v1/health/live",
        }
        if request.url.path in exempt_paths:
            return await call_next(request)

        auth_dev_mode = os.getenv("AUTH_DEV_MODE", "false").lower() in {"1", "true", "yes"}
        environment = os.getenv("ENVIRONMENT", "development").lower()
        if auth_dev_mode and environment in {"dev", "development", "local", "test"}:
            auth_header = request.headers.get("Authorization", "")
            token = (
                auth_header.replace("Bearer ", "", 1).strip()
                if auth_header.startswith("Bearer ")
                else None
            )
            claims = _dev_claims_from_jwt(token) if token else None
            tenant_id = (
                request.headers.get("X-Tenant-ID")
                or (claims.get("tenant_id") if claims else None)
                or os.getenv("AUTH_DEV_TENANT_ID", "dev-tenant")
            )
            roles_raw = (
                ",".join(claims.get("roles", []))
                if claims and isinstance(claims.get("roles"), list)
                else claims.get("roles")
                if claims and isinstance(claims.get("roles"), str)
                else os.getenv("AUTH_DEV_ROLES", "PMO_ADMIN")
            )
            roles = [role.strip() for role in str(roles_raw).split(",") if role.strip()]
            subject = (
                claims.get("sub")
                if claims
                else request.headers.get("X-Dev-User", "dev-user")
            )
            auth_context = AuthContext(
                tenant_id=tenant_id,
                subject=subject,
                roles=roles,
                claims=claims or {"roles": roles, "sub": subject},
            )
            request.state.auth = auth_context
            body = await request.body()
            request._body = body
            classification = _classification_from_body(body)
            permission = _required_permission(request)
            try:
                await _evaluate_rbac(auth_context, permission, classification)
                resource = None
                if body:
                    try:
                        resource = json.loads(body.decode("utf-8"))
                    except json.JSONDecodeError:
                        return JSONResponse(status_code=400, content={"detail": "Invalid JSON payload"})
                await _evaluate_abac(auth_context, permission, resource, request)
            except HTTPException as exc:
                return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
            response = await call_next(request)
            return response

        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "", 1).strip()
        tenant_id = request.headers.get("X-Tenant-ID")

        if not token or not tenant_id:
            return JSONResponse(status_code=401, content={"detail": "Missing JWT or tenant header"})

        try:
            claims = await _validate_jwt(token)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

        roles_claim = os.getenv("IDENTITY_ROLES_CLAIM", "roles")
        roles = _get_claim(claims, roles_claim) or claims.get("role") or claims.get("groups") or []
        if isinstance(roles, str):
            roles = [role.strip() for role in roles.replace(",", " ").split() if role.strip()]

        tenant_claim = os.getenv("IDENTITY_TENANT_CLAIM", "tenant_id")
        claim_tenant = _get_claim(claims, tenant_claim)
        if not claim_tenant:
            return JSONResponse(status_code=403, content={"detail": "Tenant claim missing"})
        if claim_tenant != tenant_id:
            return JSONResponse(status_code=403, content={"detail": "Tenant mismatch"})

        auth_context = AuthContext(
            tenant_id=tenant_id,
            subject=claims.get("sub", "unknown"),
            roles=roles,
            claims=claims,
        )
        request.state.auth = auth_context

        body = await request.body()
        request._body = body
        classification = _classification_from_body(body)
        permission = _required_permission(request)

        try:
            await _evaluate_rbac(auth_context, permission, classification)
            resource = json.loads(body.decode("utf-8")) if body else None
            await _evaluate_abac(auth_context, permission, resource, request)
        except (HTTPException, json.JSONDecodeError) as exc:
            if isinstance(exc, HTTPException):
                return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
            return JSONResponse(status_code=400, content={"detail": "Invalid JSON payload"})

        response = await call_next(request)
        return response


class FieldMaskingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if not hasattr(request.state, "auth"):
            return response

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return response

        body = b"".join([chunk async for chunk in response.body_iterator])
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
