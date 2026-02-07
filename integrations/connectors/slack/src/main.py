from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Iterable

from integrations.connectors.sdk.src.base_connector import ConnectorCategory, ConnectorConfig, SyncDirection, SyncFrequency
from integrations.connectors.sdk.src.http_client import HttpClient
from integrations.connectors.sdk.src.runtime import ConnectorRuntime
from integrations.connectors.sdk.src.secrets import resolve_secret

from .slack_connector import SlackConnector

CONNECTOR_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class SlackConfig:
    api_url: str
    bot_token: str
    rate_limit_per_minute: int

    @classmethod
    def from_env(cls, rate_limit_per_minute: int) -> "SlackConfig":
        api_url = resolve_secret(os.getenv("SLACK_API_URL")) or "https://slack.com/api"
        bot_token = resolve_secret(os.getenv("SLACK_BOT_TOKEN"))
        if not bot_token:
            raise ValueError("SLACK_BOT_TOKEN is required for Slack sync")
        return cls(api_url=api_url, bot_token=bot_token, rate_limit_per_minute=rate_limit_per_minute)


def _build_connector(config: SlackConfig, transport: Any | None = None) -> SlackConnector:
    connector_config = ConnectorConfig(
        connector_id="slack",
        name="Slack",
        category=ConnectorCategory.COLLABORATION,
        enabled=True,
        sync_direction=SyncDirection.BIDIRECTIONAL,
        sync_frequency=SyncFrequency.MANUAL,
        instance_url=config.api_url,
        project_key="",
    )
    client = HttpClient(
        base_url=config.api_url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {config.bot_token}",
        },
        timeout=20.0,
        rate_limit_per_minute=config.rate_limit_per_minute,
        transport=transport,
    )
    return SlackConnector(connector_config, client=client, transport=transport)


def _epoch_to_iso(epoch_seconds: int | float | None) -> str:
    if not epoch_seconds:
        return "1970-01-01T00:00:00Z"
    return datetime.fromtimestamp(float(epoch_seconds), tz=timezone.utc).isoformat()


def _slack_channel_records(channels: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for channel in channels:
        records.append(
            {
                "source": "project",
                "id": channel.get("id"),
                "name": channel.get("name"),
                "status": "active",
                "start_date": None,
                "end_date": None,
                "owner": channel.get("creator"),
            }
        )
    return records


def _slack_user_records(users: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for user in users:
        profile = user.get("profile") or {}
        records.append(
            {
                "source": "resource",
                "id": user.get("id"),
                "name": profile.get("real_name") or user.get("name"),
                "role": "admin" if user.get("is_admin") else "member",
                "location": profile.get("tz_label"),
                "status": "inactive" if user.get("deleted") else "active",
                "created_at": _epoch_to_iso(user.get("updated")),
                "metadata": {
                    "email": profile.get("email"),
                    "title": profile.get("title"),
                    "is_bot": user.get("is_bot"),
                },
            }
        )
    return records


def _message_payloads(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for record in records:
        channel = (
            record.get("channel")
            or record.get("channel_id")
            or record.get("conversation_id")
            or record.get("id")
        )
        text = (
            record.get("text")
            or record.get("message")
            or record.get("body")
            or record.get("title")
        )
        if not channel or not text:
            continue
        payloads.append(
            {
                "channel": channel,
                "text": text,
                "blocks": record.get("blocks"),
                "attachments": record.get("attachments"),
            }
        )
    return payloads


def run_sync(
    fixture_path: Path | None,
    tenant_id: str,
    *,
    live: bool = False,
    include_schema: bool = False,
    transport: Any | None = None,
) -> list[dict[str, Any]]:
    runtime = ConnectorRuntime(CONNECTOR_ROOT)
    if fixture_path and not live:
        return runtime.run_sync(fixture_path, tenant_id, include_schema=include_schema)
    if not live:
        raise ValueError("Fixture path is required when live mode is disabled")
    rate_limit = runtime.manifest.sync.get("rate_limit_per_minute", 60)
    config = SlackConfig.from_env(rate_limit)
    connector = _build_connector(config, transport=transport)
    channels = connector.read("channels")
    users = connector.read("users")
    records = _slack_channel_records(channels)
    records.extend(_slack_user_records(users))
    return runtime.apply_mappings(records, tenant_id, include_schema=include_schema)


def run_write(
    fixture_path: Path | None,
    tenant_id: str,
    *,
    live: bool = False,
    data: list[dict[str, Any]] | None = None,
    transport: Any | None = None,
) -> list[dict[str, Any]]:
    runtime = ConnectorRuntime(CONNECTOR_ROOT)
    if fixture_path:
        raw = json.loads(fixture_path.read_text())
        if not isinstance(raw, list):
            raise ValueError("Fixture must be a list of records")
        payload = raw
    elif data is not None:
        payload = data
    else:
        raise ValueError("No records provided for write operation")

    messages = _message_payloads(payload)
    if not messages:
        raise ValueError("No valid messages found to send to Slack")
    if not live:
        return runtime.apply_mappings(payload, tenant_id, include_schema=False)
    rate_limit = runtime.manifest.sync.get("rate_limit_per_minute", 60)
    config = SlackConfig.from_env(rate_limit)
    connector = _build_connector(config, transport=transport)
    if not connector.authenticate():
        raise RuntimeError("Failed to authenticate with Slack")
    results: list[dict[str, Any]] = []
    client = connector._build_client()
    for message in messages:
        response = client.request("POST", "/chat.postMessage", json=message)
        results.append(response.json())
    return results


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Run connector sync against a fixture file")
    parser.add_argument("fixture", nargs="?", type=str, help="Path to fixture JSON")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument("--live", action="store_true", help="Run against live API using env vars")
    parser.add_argument("--write", action="store_true", help="Send outbound messages to Slack")
    args = parser.parse_args()

    fixture = Path(args.fixture) if args.fixture else None
    if args.write:
        output = run_write(fixture, args.tenant, live=args.live)
    else:
        output = run_sync(fixture, args.tenant, live=args.live)
    print(json.dumps(output, indent=2))
