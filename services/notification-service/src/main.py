from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for root in (REPO_ROOT, SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from packages.version import API_VERSION  # noqa: E402
from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from security.auth import AuthTenantMiddleware  # noqa: E402
from security.errors import register_error_handlers  # noqa: E402
from security.headers import SecurityHeadersMiddleware  # noqa: E402

logger = logging.getLogger("notification-service")
logging.basicConfig(level=logging.INFO)

DEFAULT_TEMPLATES_DIR = REPO_ROOT / "services" / "notification-service" / "templates"
DEFAULT_OUTBOX_DIR = REPO_ROOT / "services" / "notification-service" / "outbox"
DEFAULT_DLQ_DIR = REPO_ROOT / "services" / "notification-service" / "dead-letter"
HTTP_TIMEOUT = 5
RATE_LIMIT = os.getenv("NOTIFICATION_SERVICE_RATE_LIMIT", "100/minute")

http_retry = retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    reraise=True,
)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "notification-service"
    dependencies: dict[str, str] = Field(default_factory=dict)


class NotificationRequest(BaseModel):
    template: str = Field(..., description="Template filename without extension")
    variables: dict[str, Any] = Field(default_factory=dict)
    channel: str = "stdout"
    recipient: str | None = None


class NotificationResponse(BaseModel):
    delivery_id: str
    status: str
    rendered: str
    delivered_to: str
    timestamp: datetime


app = FastAPI(title="Notification Service", version=API_VERSION, openapi_prefix="/v1")
api_router = APIRouter(prefix="/v1")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz", "/version"})
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SlowAPIMiddleware)
configure_tracing("notification-service")
configure_metrics("notification-service")
app.add_middleware(TraceMiddleware, service_name="notification-service")
app.add_middleware(RequestMetricsMiddleware, service_name="notification-service")
register_error_handlers(app)


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    templates_dir = Path(os.getenv("NOTIFICATION_TEMPLATES_DIR", str(DEFAULT_TEMPLATES_DIR)))
    outbox_dir = Path(os.getenv("NOTIFICATION_OUTBOX_DIR", str(DEFAULT_OUTBOX_DIR)))
    dlq_dir = Path(os.getenv("NOTIFICATION_DLQ_DIR", str(DEFAULT_DLQ_DIR)))
    dependencies = {
        "templates": "ok" if templates_dir.exists() else "down",
        "outbox": "ok" if outbox_dir.exists() or outbox_dir.parent.exists() else "degraded",
        "dead_letter": "ok" if dlq_dir.exists() or dlq_dir.parent.exists() else "degraded",
    }
    status = "ok" if all(value == "ok" for value in dependencies.values()) else "degraded"
    return HealthResponse(status=status, dependencies=dependencies)


@app.get("/version")
async def version() -> dict[str, str]:
    return {
        "service": "notification-service",
        "api_version": API_VERSION,
        "build_sha": os.getenv("BUILD_SHA", "unknown"),
    }


def _load_template(name: str) -> str:
    templates_dir = Path(os.getenv("NOTIFICATION_TEMPLATES_DIR", str(DEFAULT_TEMPLATES_DIR)))
    path = templates_dir / f"{name}.txt"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    return path.read_text(encoding="utf-8")


def _deliver(rendered: str, recipient: str | None, channel: str, delivery_id: str) -> str:
    destination = recipient or "stdout"
    if channel == "stdout":
        logger.info("notification_delivered", extra={"delivery_id": delivery_id, "to": destination})
        print(rendered)
    else:
        outbox_dir = Path(os.getenv("NOTIFICATION_OUTBOX_DIR", str(DEFAULT_OUTBOX_DIR)))
        outbox_dir.mkdir(parents=True, exist_ok=True)
        out_file = outbox_dir / f"{delivery_id}.txt"
        out_file.write_text(rendered, encoding="utf-8")
        destination = str(out_file)
    return delivery_id, destination


def _write_dead_letter(payload: dict[str, Any], error: str) -> None:
    dlq_dir = Path(os.getenv("NOTIFICATION_DLQ_DIR", str(DEFAULT_DLQ_DIR)))
    dlq_dir.mkdir(parents=True, exist_ok=True)
    record = payload.copy()
    record["error"] = error
    record["failed_at"] = datetime.now(timezone.utc).isoformat()
    dlq_path = dlq_dir / f"{record.get('delivery_id', 'unknown')}.json"
    dlq_path.write_text(json.dumps(record, indent=2), encoding="utf-8")


def _parse_channel_priority() -> list[str]:
    configured = os.getenv("NOTIFICATION_CHANNEL_PRIORITY", "teams,slack,acs,stdout")
    channels: list[str] = []
    for name in configured.split(","):
        channel = name.strip().lower()
        if channel and channel not in channels:
            channels.append(channel)
    return channels


def _coerce_recipient_to_target(recipient: str | None, fallback: str | None) -> str | None:
    return recipient or fallback


@http_retry
async def _fetch_graph_token() -> str:
    token = os.getenv("NOTIFICATION_TEAMS_GRAPH_ACCESS_TOKEN")
    if token:
        return token

    tenant_id = os.getenv("NOTIFICATION_TEAMS_TENANT_ID")
    client_id = os.getenv("NOTIFICATION_TEAMS_CLIENT_ID")
    client_secret = os.getenv("NOTIFICATION_TEAMS_CLIENT_SECRET")
    if not all([tenant_id, client_id, client_secret]):
        raise ValueError("Teams Graph API credentials are not configured")

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.post(token_url, data=data)
        response.raise_for_status()
        payload = response.json()
    return payload["access_token"]


def _resolve_teams_target(recipient: str | None) -> tuple[str | None, str | None, str | None]:
    chat_id = os.getenv("NOTIFICATION_TEAMS_CHAT_ID")
    team_id = os.getenv("NOTIFICATION_TEAMS_TEAM_ID")
    channel_id = os.getenv("NOTIFICATION_TEAMS_CHANNEL_ID")

    if recipient:
        if recipient.startswith("chat:"):
            chat_id = recipient.removeprefix("chat:")
        elif recipient.startswith("channel:"):
            channel_id = recipient.removeprefix("channel:")
        elif not chat_id and not team_id:
            chat_id = recipient
        elif team_id and not channel_id:
            channel_id = recipient

    return chat_id, team_id, channel_id


@http_retry
async def _send_teams_notification(rendered: str, recipient: str | None) -> str:
    webhook_url = os.getenv("NOTIFICATION_TEAMS_WEBHOOK_URL")
    if webhook_url:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(webhook_url, json={"text": rendered})
            response.raise_for_status()
        return "teams:webhook"

    token = await _fetch_graph_token()
    base_url = os.getenv("NOTIFICATION_TEAMS_GRAPH_BASE_URL", "https://graph.microsoft.com/v1.0")
    chat_id, team_id, channel_id = _resolve_teams_target(recipient)
    if chat_id:
        path = f"/chats/{chat_id}/messages"
        target = f"teams:chat:{chat_id}"
    elif team_id and channel_id:
        path = f"/teams/{team_id}/channels/{channel_id}/messages"
        target = f"teams:channel:{team_id}/{channel_id}"
    else:
        raise ValueError("Teams Graph target is not configured")

    payload = {"body": {"content": rendered}}
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.post(
            f"{base_url}{path}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
    return target


@http_retry
async def _send_slack_notification(rendered: str, recipient: str | None) -> str:
    webhook_url = os.getenv("NOTIFICATION_SLACK_WEBHOOK_URL")
    if webhook_url:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(webhook_url, json={"text": rendered})
            response.raise_for_status()
        return "slack:webhook"

    token = os.getenv("NOTIFICATION_SLACK_BOT_TOKEN")
    channel = _coerce_recipient_to_target(recipient, os.getenv("NOTIFICATION_SLACK_CHANNEL"))
    if not token or not channel:
        raise ValueError("Slack API credentials are not configured")

    base_url = os.getenv("NOTIFICATION_SLACK_API_BASE_URL", "https://slack.com/api")
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.post(
            f"{base_url}/chat.postMessage",
            json={"channel": channel, "text": rendered},
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        payload = response.json()
    if not payload.get("ok", False):
        raise ValueError(f"Slack API error: {payload.get('error', 'unknown')}")
    return f"slack:channel:{channel}"


@http_retry
async def _send_acs_notification(rendered: str, recipient: str | None) -> str:
    endpoint = os.getenv("NOTIFICATION_ACS_ENDPOINT")
    token = os.getenv("NOTIFICATION_ACS_ACCESS_TOKEN")
    target = _coerce_recipient_to_target(recipient, os.getenv("NOTIFICATION_ACS_DEVICE_TOKEN"))
    if not endpoint or not token or not target:
        raise ValueError("ACS push notification configuration is incomplete")

    api_version = os.getenv("NOTIFICATION_ACS_API_VERSION", "2023-03-31")
    if "api-version=" not in endpoint:
        separator = "&" if "?" in endpoint else "?"
        endpoint = f"{endpoint}{separator}api-version={api_version}"

    payload = {
        "to": target,
        "message": rendered,
    }
    application_id = os.getenv("NOTIFICATION_ACS_APPLICATION_ID")
    if application_id:
        payload["applicationId"] = application_id

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.post(
            endpoint,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
    return f"acs:device:{target}"


@api_router.post("/notifications/send", response_model=NotificationResponse)
@limiter.limit(RATE_LIMIT)
async def send_notification(request: NotificationRequest) -> NotificationResponse:
    template = _load_template(request.template)
    try:
        rendered = template.format(**request.variables)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"Missing template variable: {exc}") from exc

    delivery_id = str(uuid4())
    priority = _parse_channel_priority()
    requested_channel = request.channel.lower().strip() if request.channel else ""
    channels_to_try: list[str] = []
    if requested_channel and requested_channel != "auto":
        channels_to_try.append(requested_channel)
    for channel in priority:
        if channel not in channels_to_try:
            channels_to_try.append(channel)

    last_error: Exception | None = None
    destination = ""
    for channel in channels_to_try:
        try:
            if channel == "teams":
                destination = await _send_teams_notification(rendered, request.recipient)
            elif channel == "slack":
                destination = await _send_slack_notification(rendered, request.recipient)
            elif channel == "acs":
                destination = await _send_acs_notification(rendered, request.recipient)
            else:
                _, destination = _deliver(rendered, request.recipient, channel, delivery_id)
            break
        except RetryError as exc:
            last_error = exc
            logger.warning(
                "notification_channel_retry_exhausted",
                extra={"channel": channel, "error": str(exc), "delivery_id": delivery_id},
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning(
                "notification_channel_failed",
                extra={"channel": channel, "error": str(exc), "delivery_id": delivery_id},
            )
    else:
        detail = f"Notification delivery failed: {last_error}" if last_error else "No channel available"
        try:
            _write_dead_letter(
                {
                    "delivery_id": delivery_id,
                    "template": request.template,
                    "channel": request.channel,
                    "recipient": request.recipient,
                    "variables": request.variables,
                },
                error=detail,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("notification_dlq_write_failed", extra={"error": str(exc)})
        raise HTTPException(status_code=502, detail=detail)

    timestamp = datetime.now(timezone.utc)
    return NotificationResponse(
        delivery_id=delivery_id,
        status="delivered",
        rendered=rendered,
        delivered_to=destination,
        timestamp=timestamp,
    )


app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
