from __future__ import annotations

import json
import logging
import os
import secrets
import sys
import time
import uuid
from pathlib import Path
from sqlite3 import Error as SqliteError
from sqlite3 import IntegrityError
from typing import Any

import httpx
import jwt
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from jwt import InvalidTokenError
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for root in (REPO_ROOT, SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from packages.version import API_VERSION  # noqa: E402
from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from saml import (  # noqa: E402
    SamlUnavailableError,
    build_auth,
    build_saml_settings,
    load_saml_config,
    prepare_fastapi_request,
)
from scim_models import (  # noqa: E402
    SCIM_CORE_GROUP,
    SCIM_CORE_USER,
    SCIM_EXTENSION_ROLES,
    SCIM_LIST_RESPONSE,
    PatchRequest,
    ScimGroup,
    ScimGroupCreate,
    ScimListResponse,
    ScimUser,
    ScimUserCreate,
)
from scim_store import ScimStore  # noqa: E402
from security.auth import authenticate_request  # noqa: E402
from security.errors import register_error_handlers  # noqa: E402
from security.headers import SecurityHeadersMiddleware  # noqa: E402
from security.secrets import resolve_secret  # noqa: E402

logger = logging.getLogger("identity-access")
logging.basicConfig(level=logging.INFO)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "identity-access"
    dependencies: dict[str, str] = Field(default_factory=dict)


class AuthValidateRequest(BaseModel):
    token: str


class AuthValidateResponse(BaseModel):
    active: bool
    subject: str | None = None
    claims: dict[str, Any] | None = None


class SamlTokenResponse(BaseModel):
    token: str
    subject: str
    attributes: dict[str, Any]


class JwksCache:
    def __init__(self) -> None:
        self.jwks: dict[str, Any] | None = None
        self.fetched_at: float = 0

    def get(self) -> dict[str, Any] | None:
        if self.jwks and (time.time() - self.fetched_at) < 300:
            return self.jwks
        return None

    def set(self, jwks: dict[str, Any]) -> None:
        self.jwks = jwks
        self.fetched_at = time.time()


JWKS_CACHE = JwksCache()
SERVICE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCIM_DB_PATH = SERVICE_ROOT / "storage" / "scim.db"

app = FastAPI(title="Identity Access Service", version=API_VERSION, openapi_prefix="/v1")
api_router = APIRouter(prefix="/v1")
configure_tracing("identity-access")
configure_metrics("identity-access")
app.add_middleware(TraceMiddleware, service_name="identity-access")
app.add_middleware(RequestMetricsMiddleware, service_name="identity-access")
app.add_middleware(SecurityHeadersMiddleware)
register_error_handlers(app)

token_validation_failures = configure_metrics("identity-access").create_counter(
    name="identity_token_validation_failures_total",
    description="Token validation failures",
    unit="1",
)

scim_store = ScimStore(Path(os.getenv("SCIM_DB_PATH", DEFAULT_SCIM_DB_PATH)))


@app.middleware("http")
async def auth_tenant_middleware(request: Request, call_next):
    if request.url.path in {"/healthz", "/version", "/v1/auth/validate"} or request.url.path.startswith(
        "/v1/scim/"
    ):
        return await call_next(request)
    if request.url.path.startswith("/v1/auth/saml/"):
        return await call_next(request)
    try:
        auth_context = await authenticate_request(request)
    except HTTPException as exc:
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        payload = {"error": {"message": message, "code": f"http_{exc.status_code}", "details": exc.detail}}
        return JSONResponse(status_code=exc.status_code, content=payload)
    request.state.auth = auth_context
    return await call_next(request)


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    dependencies = {"scim_db": "unknown", "saml_config": "unknown"}
    try:
        scim_store.ping()
        dependencies["scim_db"] = "ok"
    except SqliteError:
        dependencies["scim_db"] = "down"
    try:
        load_saml_config()
        dependencies["saml_config"] = "ok"
    except SamlUnavailableError:
        dependencies["saml_config"] = "degraded"
    except (RuntimeError, ValueError, OSError):
        dependencies["saml_config"] = "down"
    status = "ok" if all(value == "ok" for value in dependencies.values()) else "degraded"
    return HealthResponse(status=status, dependencies=dependencies)


@app.get("/version")
async def version() -> dict[str, str]:
    return {
        "service": "identity-access",
        "api_version": API_VERSION,
        "build_sha": os.getenv("BUILD_SHA", "unknown"),
    }


def _get_env(name: str) -> str | None:
    return resolve_secret(os.getenv(name))


def _require_scim_context(
    authorization: str | None = Header(default=None, alias="Authorization"),
    tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> str:
    token = _get_env("SCIM_SERVICE_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="SCIM token not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing SCIM token")
    candidate = authorization.replace("Bearer ", "", 1).strip()
    if not secrets.compare_digest(token, candidate):
        raise HTTPException(status_code=401, detail="Invalid SCIM token")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Missing tenant header")
    return tenant_id


def _scim_user_payload(user) -> dict[str, Any]:
    return ScimUser(
        schemas=[SCIM_CORE_USER, SCIM_EXTENSION_ROLES],
        id=user.id,
        userName=user.user_name,
        displayName=user.display_name,
        active=user.active,
        emails=user.emails or None,
        groups=user.groups or None,
        **{SCIM_EXTENSION_ROLES: {"roles": user.roles}},
    ).model_dump(by_alias=True, exclude_none=True)


def _scim_group_payload(group) -> dict[str, Any]:
    return ScimGroup(
        schemas=[SCIM_CORE_GROUP],
        id=group.id,
        displayName=group.display_name,
        members=group.members or None,
    ).model_dump(by_alias=True, exclude_none=True)


def _parse_user_filter(filter_value: str | None) -> str | None:
    if not filter_value:
        return None
    value = filter_value.strip()
    if value.startswith("userName eq "):
        raw = value[len("userName eq ") :].strip().strip('"')
        if raw:
            return raw
    raise HTTPException(status_code=400, detail="Unsupported SCIM filter")


@api_router.post("/auth/validate", response_model=AuthValidateResponse)
async def validate_token(request: AuthValidateRequest) -> AuthValidateResponse:
    jwt_secret = _get_env("IDENTITY_JWT_SECRET")
    jwks_url = _get_env("IDENTITY_JWKS_URL")
    audience = _get_env("IDENTITY_AUDIENCE")
    issuer = _get_env("IDENTITY_ISSUER")

    try:
        if jwks_url:
            claims = _verify_with_jwks(request.token, jwks_url, audience, issuer)
        elif jwt_secret:
            claims = jwt.decode(
                request.token,
                jwt_secret,
                algorithms=["HS256"],
                audience=audience,
                issuer=issuer,
                options={"verify_aud": bool(audience), "verify_iss": bool(issuer)},
            )
        else:
            raise HTTPException(status_code=500, detail="JWT configuration missing")
    except InvalidTokenError as exc:
        logger.warning("token_validation_failed", extra={"error": str(exc)})
        token_validation_failures.add(1, {})
        return AuthValidateResponse(active=False)

    return AuthValidateResponse(active=True, subject=claims.get("sub"), claims=claims)


@api_router.get("/auth/saml/metadata")
async def saml_metadata() -> Response:
    try:
        config = load_saml_config()
        settings = build_saml_settings(config)
    except SamlUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)
    if errors:
        raise HTTPException(status_code=500, detail=f"SAML metadata invalid: {errors}")
    return Response(content=metadata, media_type="application/xml")


@api_router.get("/auth/saml/login")
async def saml_login(request: Request) -> RedirectResponse:
    try:
        config = load_saml_config()
        settings = build_saml_settings(config)
    except SamlUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    request_data = prepare_fastapi_request(request)
    auth = build_auth({**request_data, "post_data": {}}, old_settings=settings)
    redirect_url = auth.login()
    return RedirectResponse(url=redirect_url)


@api_router.post("/auth/saml/acs", response_model=SamlTokenResponse)
async def saml_acs(request: Request) -> SamlTokenResponse:
    try:
        config = load_saml_config()
        settings = build_saml_settings(config)
    except SamlUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    form = await request.form()
    request_data = prepare_fastapi_request(request)
    auth = build_auth({**request_data, "post_data": dict(form)}, old_settings=settings)
    auth.process_response()
    errors = auth.get_errors()
    if errors:
        raise HTTPException(status_code=401, detail=f"SAML response invalid: {errors}")
    if not auth.is_authenticated():
        raise HTTPException(status_code=401, detail="SAML authentication failed")
    attributes = auth.get_attributes() or {}
    subject = auth.get_nameid() or attributes.get("email", ["saml-user"])[0]
    jwt_secret = _get_env("IDENTITY_JWT_SECRET")
    if not jwt_secret:
        raise HTTPException(status_code=500, detail="JWT configuration missing")
    issuer = _get_env("IDENTITY_ISSUER")
    audience = _get_env("IDENTITY_AUDIENCE")
    now = int(time.time())
    claims = {
        "sub": subject,
        "iat": now,
        "exp": now + 3600,
        "aud": audience,
        "iss": issuer,
        "roles": attributes.get("roles", []),
        "tenant_id": attributes.get("tenant_id", [None])[0],
    }
    token = jwt.encode(
        {k: v for k, v in claims.items() if v is not None}, jwt_secret, algorithm="HS256"
    )
    return SamlTokenResponse(token=token, subject=subject, attributes=attributes)


@api_router.post("/scim/v2/Users", status_code=201)
async def scim_create_user(
    payload: ScimUserCreate, tenant_id: str = Depends(_require_scim_context)
) -> dict[str, Any]:
    group_ids = [group.value for group in payload.groups or []]
    user_id = str(uuid.uuid4())
    try:
        user = scim_store.create_user(
            tenant_id,
            user_id=user_id,
            user_name=payload.user_name,
            display_name=payload.display_name,
            active=payload.active if payload.active is not None else True,
            emails=[email.model_dump(by_alias=True) for email in (payload.emails or [])],
            group_ids=group_ids,
        )
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="User already exists or group invalid") from exc
    return _scim_user_payload(user)


@api_router.get("/scim/v2/Users")
async def scim_list_users(
    filter: str | None = None, tenant_id: str = Depends(_require_scim_context)
) -> dict[str, Any]:
    user_name = _parse_user_filter(filter)
    users = scim_store.list_users(tenant_id, user_name=user_name)
    resources = [_scim_user_payload(user) for user in users]
    return ScimListResponse(
        schemas=[SCIM_LIST_RESPONSE],
        totalResults=len(resources),
        itemsPerPage=len(resources),
        startIndex=1,
        Resources=resources,
    ).model_dump(by_alias=True)


@api_router.get("/scim/v2/Users/{user_id}")
async def scim_get_user(
    user_id: str, tenant_id: str = Depends(_require_scim_context)
) -> dict[str, Any]:
    try:
        user = scim_store.get_user(tenant_id, user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="User not found") from exc
    return _scim_user_payload(user)


@api_router.patch("/scim/v2/Users/{user_id}")
async def scim_patch_user(
    user_id: str,
    payload: PatchRequest,
    tenant_id: str = Depends(_require_scim_context),
) -> dict[str, Any]:
    display_name = None
    active = None
    emails = None
    group_ids = None
    for operation in payload.operations:
        op = operation.op.lower()
        path = (operation.path or "").strip()
        value = operation.value
        if path in {"displayName", "displayname"} or (
            not path and isinstance(value, dict) and "displayName" in value
        ):
            if op not in {"add", "replace"}:
                raise HTTPException(status_code=400, detail="Unsupported SCIM patch operation")
            display_name = value.get("displayName") if isinstance(value, dict) else value
        elif path in {"active"} or (not path and isinstance(value, dict) and "active" in value):
            if op not in {"add", "replace"}:
                raise HTTPException(status_code=400, detail="Unsupported SCIM patch operation")
            active = value.get("active") if isinstance(value, dict) else value
        elif path in {"emails"} or (not path and isinstance(value, dict) and "emails" in value):
            if op not in {"add", "replace"}:
                raise HTTPException(status_code=400, detail="Unsupported SCIM patch operation")
            emails = value.get("emails") if isinstance(value, dict) else value
        elif path in {"groups"} or (not path and isinstance(value, dict) and "groups" in value):
            if op not in {"add", "replace"}:
                raise HTTPException(status_code=400, detail="Unsupported SCIM patch operation")
            groups_value = value.get("groups") if isinstance(value, dict) else value
            group_ids = [item.get("value") for item in (groups_value or []) if item.get("value")]
        elif op == "remove" and path == "groups":
            group_ids = []
        else:
            raise HTTPException(status_code=400, detail="Unsupported SCIM patch operation")

    try:
        user = scim_store.update_user(
            tenant_id,
            user_id,
            display_name=display_name,
            active=active,
            emails=emails,
            group_ids=group_ids,
        )
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Invalid group assignment") from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="User not found") from exc
    return _scim_user_payload(user)


@api_router.post("/scim/v2/Groups", status_code=201)
async def scim_create_group(
    payload: ScimGroupCreate, tenant_id: str = Depends(_require_scim_context)
) -> dict[str, Any]:
    group_id = str(uuid.uuid4())
    members = [member.value for member in payload.members or []]
    try:
        group = scim_store.create_group(
            tenant_id,
            group_id=group_id,
            display_name=payload.display_name,
            members=members,
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409, detail="Group already exists or member invalid"
        ) from exc
    return _scim_group_payload(group)


@api_router.get("/scim/v2/Groups")
async def scim_list_groups(tenant_id: str = Depends(_require_scim_context)) -> dict[str, Any]:
    groups = scim_store.list_groups(tenant_id)
    resources = [_scim_group_payload(group) for group in groups]
    return ScimListResponse(
        schemas=[SCIM_LIST_RESPONSE],
        totalResults=len(resources),
        itemsPerPage=len(resources),
        startIndex=1,
        Resources=resources,
    ).model_dump(by_alias=True)


@api_router.patch("/scim/v2/Groups/{group_id}")
async def scim_patch_group(
    group_id: str,
    payload: PatchRequest,
    tenant_id: str = Depends(_require_scim_context),
) -> dict[str, Any]:
    add_members: list[str] = []
    remove_members: list[str] = []
    for operation in payload.operations:
        op = operation.op.lower()
        path = (operation.path or "").strip()
        value = operation.value
        if path in {"members"} or (not path and isinstance(value, dict) and "members" in value):
            members_value = value.get("members") if isinstance(value, dict) else value
            member_ids = [
                member.get("value") for member in (members_value or []) if member.get("value")
            ]
            if op in {"add", "replace"}:
                add_members.extend(member_ids)
            elif op == "remove":
                remove_members.extend(member_ids)
            else:
                raise HTTPException(status_code=400, detail="Unsupported SCIM patch operation")
        elif op == "remove" and path == "members":
            try:
                existing = scim_store.get_group(tenant_id, group_id)
            except KeyError as exc:
                raise HTTPException(status_code=404, detail="Group not found") from exc
            remove_members = [member["value"] for member in existing.members]
        else:
            raise HTTPException(status_code=400, detail="Unsupported SCIM patch operation")

    try:
        group = scim_store.update_group_members(
            tenant_id,
            group_id,
            add_members=add_members or None,
            remove_members=remove_members or None,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Group not found") from exc
    return _scim_group_payload(group)


@api_router.get("/scim/internal/roles/{user_id}")
async def scim_get_roles(
    user_id: str, tenant_id: str = Depends(_require_scim_context)
) -> dict[str, Any]:
    try:
        user = scim_store.get_user(tenant_id, user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="User not found") from exc
    return {"user_id": user.id, "roles": user.roles}


def _verify_with_jwks(
    token: str, jwks_url: str, audience: str | None, issuer: str | None
) -> dict[str, Any]:
    cached = JWKS_CACHE.get()
    if cached is None:
        response = httpx.get(jwks_url, timeout=5.0)
        response.raise_for_status()
        cached = response.json()
        JWKS_CACHE.set(cached)

    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    keys = cached.get("keys", [])
    key = next((k for k in keys if k.get("kid") == kid), None)
    if not key:
        raise InvalidTokenError("JWKS key not found")

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
    return jwt.decode(
        token,
        public_key,
        algorithms=[unverified_header.get("alg", "RS256")],
        audience=audience,
        issuer=issuer,
        options={"verify_aud": bool(audience), "verify_iss": bool(issuer)},
    )


app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
