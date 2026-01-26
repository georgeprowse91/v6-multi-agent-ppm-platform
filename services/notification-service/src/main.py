from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
if str(SECURITY_ROOT) not in sys.path:
    sys.path.insert(0, str(SECURITY_ROOT))

from security.auth import AuthTenantMiddleware  # noqa: E402

logger = logging.getLogger("notification-service")
logging.basicConfig(level=logging.INFO)

DEFAULT_TEMPLATES_DIR = REPO_ROOT / "services" / "notification-service" / "templates"
DEFAULT_OUTBOX_DIR = REPO_ROOT / "services" / "notification-service" / "outbox"


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "notification-service"


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


app = FastAPI(title="Notification Service", version="0.1.0")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz"})


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse()


def _load_template(name: str) -> str:
    templates_dir = Path(os.getenv("NOTIFICATION_TEMPLATES_DIR", str(DEFAULT_TEMPLATES_DIR)))
    path = templates_dir / f"{name}.txt"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    return path.read_text(encoding="utf-8")


def _deliver(rendered: str, recipient: str | None, channel: str) -> str:
    delivery_id = str(uuid4())
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


@app.post("/notifications/send", response_model=NotificationResponse)
async def send_notification(request: NotificationRequest) -> NotificationResponse:
    template = _load_template(request.template)
    try:
        rendered = template.format(**request.variables)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"Missing template variable: {exc}") from exc

    delivery_id, destination = _deliver(rendered, request.recipient, request.channel)
    timestamp = datetime.now(timezone.utc)
    return NotificationResponse(
        delivery_id=delivery_id,
        status="delivered",
        rendered=rendered,
        delivered_to=destination,
        timestamp=timestamp,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
