"""
Zoom Connector Webhooks

Handles inbound Zoom webhook events and supports webhook endpoint registration
via the Zoom REST API.

Supported event types:
    meeting.started           – A meeting has started.
    meeting.ended             – A meeting has ended.
    meeting.participant_joined  – A participant joined a meeting.
    meeting.participant_left    – A participant left a meeting.
    meeting.registration_created – A participant registered for a meeting.
    webinar.started           – A webinar has started.
    webinar.ended             – A webinar has ended.
    webinar.participant_joined  – A participant joined a webinar.
    recording.completed       – A cloud recording has completed processing.
    endpoint.url_validation   – Zoom challenge-response validation request.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported event categories
# ---------------------------------------------------------------------------

_MEETING_EVENTS = frozenset({
    "meeting.started",
    "meeting.ended",
    "meeting.participant_joined",
    "meeting.participant_left",
    "meeting.registration_created",
    "meeting.updated",
    "meeting.deleted",
})

_WEBINAR_EVENTS = frozenset({
    "webinar.started",
    "webinar.ended",
    "webinar.participant_joined",
    "webinar.participant_left",
    "webinar.registration_created",
})

_RECORDING_EVENTS = frozenset({
    "recording.completed",
    "recording.transcript_completed",
    "recording.deleted",
})


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


def verify_signature(
    payload_body: bytes,
    headers: dict[str, str],
    *,
    secret: str | None = None,
) -> bool:
    """
    Verify the Zoom webhook signature.

    Zoom signs webhook payloads using HMAC-SHA256.  The signature is included
    in the ``x-zm-signature`` header; the timestamp in ``x-zm-request-timestamp``.

    Args:
        payload_body: Raw request body bytes.
        headers: HTTP request headers.
        secret: Webhook secret token.  Falls back to ZOOM_WEBHOOK_SECRET env var.

    Returns:
        True if the signature is valid, False otherwise.
    """
    token = secret or os.getenv("ZOOM_WEBHOOK_SECRET") or ""
    if not token:
        logger.warning("ZOOM_WEBHOOK_SECRET not set; skipping signature verification")
        return True

    normalised_headers = {k.lower(): v for k, v in headers.items()}
    timestamp = normalised_headers.get("x-zm-request-timestamp", "")
    received_sig = normalised_headers.get("x-zm-signature", "")

    message = f"v0:{timestamp}:{payload_body.decode('utf-8', errors='replace')}"
    expected_sig = "v0=" + hmac.new(
        token.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected_sig, received_sig)


# ---------------------------------------------------------------------------
# Event normalisation helpers
# ---------------------------------------------------------------------------


def _extract_meeting_fields(obj: dict[str, Any]) -> dict[str, Any]:
    return {
        "meeting_id": obj.get("id"),
        "topic": obj.get("topic"),
        "host_id": obj.get("host_id"),
        "start_time": obj.get("start_time"),
        "duration": obj.get("duration"),
        "timezone": obj.get("timezone"),
        "join_url": obj.get("join_url"),
    }


def _extract_webinar_fields(obj: dict[str, Any]) -> dict[str, Any]:
    return {
        "webinar_id": obj.get("id"),
        "topic": obj.get("topic"),
        "host_id": obj.get("host_id"),
        "start_time": obj.get("start_time"),
        "duration": obj.get("duration"),
        "agenda": obj.get("agenda"),
        "join_url": obj.get("join_url"),
    }


def _extract_participant_fields(obj: dict[str, Any]) -> dict[str, Any]:
    participant = obj.get("participant", {})
    return {
        "participant_id": participant.get("user_id") or participant.get("id"),
        "participant_name": participant.get("user_name") or participant.get("name"),
        "email": participant.get("email"),
        "join_time": participant.get("join_time"),
        "leave_time": participant.get("leave_time"),
    }


def _extract_recording_fields(obj: dict[str, Any]) -> dict[str, Any]:
    return {
        "recording_id": obj.get("uuid") or obj.get("id"),
        "meeting_id": obj.get("id"),
        "topic": obj.get("topic"),
        "start_time": obj.get("start_time"),
        "duration": obj.get("duration"),
        "share_url": obj.get("share_url"),
        "recording_files": [
            {
                "file_id": f.get("id"),
                "file_type": f.get("file_type"),
                "file_size": f.get("file_size"),
                "status": f.get("status"),
                "download_url": f.get("download_url"),
            }
            for f in obj.get("recording_files", [])
        ],
    }


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------


def handle_webhook(payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """
    Handle a Zoom webhook event and return a normalised event envelope.

    The returned dict always contains:
        connector_id (str): "zoom"
        event_type (str): The Zoom event name (e.g. "meeting.started").
        event_ts (int | None): Unix-millisecond timestamp from Zoom.
        account_id (str | None): Zoom account that sent the event.
        resource_type (str): One of "meeting", "webinar", "recording", "unknown".
        resource_id (str | None): Primary resource identifier.
        details (dict): Event-specific normalised fields.
    """
    event_type: str = payload.get("event", "")
    event_ts: int | None = payload.get("event_ts")
    event_payload: dict[str, Any] = payload.get("payload", {})
    event_obj: dict[str, Any] = event_payload.get("object", {})
    account_id: str | None = event_payload.get("account_id")

    # Handle Zoom challenge-response (URL validation)
    if event_type == "endpoint.url_validation":
        plain_token = event_payload.get("plainToken", "")
        zoom_secret = os.getenv("ZOOM_WEBHOOK_SECRET", "")
        encrypted = hmac.new(
            zoom_secret.encode("utf-8"),
            plain_token.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest() if zoom_secret else ""
        return {
            "connector_id": "zoom",
            "event_type": event_type,
            "challenge_response": {
                "plainToken": plain_token,
                "encryptedToken": encrypted,
            },
        }

    # Determine resource type and extract normalised details
    if event_type in _MEETING_EVENTS:
        resource_type = "meeting"
        resource_id = str(event_obj.get("id", "")) or None
        if "participant" in event_type:
            details = {**_extract_meeting_fields(event_obj), **_extract_participant_fields(event_obj)}
        else:
            details = _extract_meeting_fields(event_obj)
    elif event_type in _WEBINAR_EVENTS:
        resource_type = "webinar"
        resource_id = str(event_obj.get("id", "")) or None
        if "participant" in event_type:
            details = {**_extract_webinar_fields(event_obj), **_extract_participant_fields(event_obj)}
        else:
            details = _extract_webinar_fields(event_obj)
    elif event_type in _RECORDING_EVENTS:
        resource_type = "recording"
        resource_id = event_obj.get("uuid") or str(event_obj.get("id", "")) or None
        details = _extract_recording_fields(event_obj)
    else:
        resource_type = "unknown"
        resource_id = str(event_obj.get("id", "")) or None
        details = event_obj
        logger.warning("Unrecognised Zoom event type: %s", event_type)

    logger.info(
        "Zoom webhook received: event=%s resource_type=%s resource_id=%s",
        event_type,
        resource_type,
        resource_id,
    )

    return {
        "connector_id": "zoom",
        "event_type": event_type,
        "event_ts": event_ts,
        "account_id": account_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details,
    }


# ---------------------------------------------------------------------------
# Webhook registration
# ---------------------------------------------------------------------------


def register_webhook(
    webhook_url: str,
    secret: str,
    config: Any | None = None,
    *,
    event_types: list[str] | None = None,
) -> dict[str, Any]:
    """
    Register a webhook delivery endpoint with Zoom via the REST API.

    Calls ``POST /v2/webhooks`` using a Server-to-Server OAuth2 token obtained
    from ``ZOOM_CLIENT_ID``, ``ZOOM_CLIENT_SECRET``, and ``ZOOM_ACCOUNT_ID``.

    Args:
        webhook_url: The HTTPS URL that Zoom will deliver events to.
        secret: Webhook verification token used by :func:`verify_signature`.
        config: Optional connector config override (unused, reserved for future).
        event_types: List of Zoom event types to subscribe to.  Defaults to
                     all meeting, webinar, and recording events.

    Returns:
        dict with keys: connector_id, status, webhook_id, webhook_url,
        subscribed_events (on success) or error (on failure).
    """
    _repo_root = Path(__file__).resolve().parents[4]
    _common_src = _repo_root / "packages" / "common" / "src"
    if str(_common_src) not in sys.path:
        sys.path.insert(0, str(_common_src))
    from common.bootstrap import ensure_monorepo_paths
    ensure_monorepo_paths(_repo_root)

    subscribed_events = event_types or sorted(_MEETING_EVENTS | _WEBINAR_EVENTS | _RECORDING_EVENTS)

    try:
        from connector_secrets import resolve_secret
        from http_client import HttpClient

        client_id = resolve_secret(os.getenv("ZOOM_CLIENT_ID")) or ""
        client_secret = resolve_secret(os.getenv("ZOOM_CLIENT_SECRET")) or ""
        account_id = resolve_secret(os.getenv("ZOOM_ACCOUNT_ID")) or ""

        if not (client_id and client_secret and account_id):
            logger.warning(
                "ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET, and ZOOM_ACCOUNT_ID are required "
                "for webhook registration; returning stub response."
            )
            return {
                "connector_id": "zoom",
                "status": "skipped",
                "reason": "missing_credentials",
                "webhook_url": webhook_url,
                "subscribed_events": subscribed_events,
            }

        # Obtain a Server-to-Server OAuth2 client-credentials token
        token_client = HttpClient(base_url="https://zoom.us", timeout=10.0)
        token_resp = token_client.request(
            "POST",
            "/oauth/token",
            params={"grant_type": "account_credentials", "account_id": account_id},
            auth=(client_id, client_secret),
        )
        access_token: str = token_resp.json().get("access_token", "")
        if not access_token:
            raise RuntimeError("Zoom token endpoint did not return an access_token")

        # Register the webhook endpoint
        api_client = HttpClient(
            base_url="https://api.zoom.us/v2",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            timeout=15.0,
        )
        body = {
            "url": webhook_url,
            "auth_user": "zoom-webhook",
            "auth_password": secret,
            "events": subscribed_events,
        }
        reg_resp = api_client.request("POST", "/webhooks", json=body)
        result = reg_resp.json()
        webhook_id: str = result.get("webhook_id", result.get("id", ""))
        logger.info(
            "Zoom webhook registered: id=%s url=%s events=%d",
            webhook_id,
            webhook_url,
            len(subscribed_events),
        )
        return {
            "connector_id": "zoom",
            "status": "registered",
            "webhook_id": webhook_id,
            "webhook_url": webhook_url,
            "subscribed_events": subscribed_events,
        }

    except Exception as exc:
        logger.error("Zoom webhook registration failed: %s", exc)
        return {
            "connector_id": "zoom",
            "status": "error",
            "error": str(exc),
            "webhook_url": webhook_url,
            "subscribed_events": subscribed_events,
        }
