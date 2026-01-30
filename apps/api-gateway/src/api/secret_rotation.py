from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from threading import Event, Thread
import httpx

from api.connector_loader import get_connector_class
from base_connector import ConnectorConfig, ConnectorConfigStore
from connector_registry import get_connector_definition

logger = logging.getLogger(__name__)


class ConnectorSecretRotationScheduler:
    def __init__(
        self,
        store: ConnectorConfigStore,
        *,
        interval_seconds: int = 3600,
        automation_webhook_url: str | None = None,
    ) -> None:
        self._store = store
        self._interval_seconds = interval_seconds
        self._automation_webhook_url = automation_webhook_url
        self._thread: Thread | None = None
        self._stop = Event()
        self._last_run: str | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    def snapshot(self) -> dict[str, str | int]:
        return {
            "last_run": self._last_run or "",
            "interval_seconds": self._interval_seconds,
        }

    def _run_loop(self) -> None:
        while not self._stop.wait(self._interval_seconds):
            self._rotate_due()

    def _rotate_due(self) -> None:
        now = datetime.now(timezone.utc)
        for config in self._store.list_all():
            definition = get_connector_definition(config.connector_id)
            if not definition or definition.auth_type != "oauth2":
                continue
            if not self._rotation_enabled(config):
                continue
            provider = self._rotation_provider(config)
            refresh_days = self._rotation_days(config, "refresh_token_rotation_days")
            client_days = self._rotation_days(config, "client_secret_rotation_days")
            refresh_due = self._is_due(config, "last_refresh_token_rotated_at", refresh_days, now)
            client_due = self._is_due(config, "last_client_secret_rotated_at", client_days, now)
            if refresh_due:
                self._rotate_refresh_token(config, provider, now)
            if client_due:
                self._rotate_client_secret(config, provider, now)
        self._last_run = now.isoformat()

    def _rotation_enabled(self, config: ConnectorConfig) -> bool:
        return bool((config.custom_fields or {}).get("rotation_enabled", False))

    def _rotation_provider(self, config: ConnectorConfig) -> str:
        provider = (config.custom_fields or {}).get("rotation_provider") or "background_job"
        return str(provider)

    def _rotation_days(self, config: ConnectorConfig, key: str) -> int:
        value = (config.custom_fields or {}).get(key)
        try:
            return int(value) if value is not None else 0
        except (TypeError, ValueError):
            return 0

    def _is_due(
        self,
        config: ConnectorConfig,
        last_key: str,
        interval_days: int,
        now: datetime,
    ) -> bool:
        if interval_days <= 0:
            return False
        last_value = (config.custom_fields or {}).get(last_key)
        if not last_value:
            return True
        try:
            last_dt = datetime.fromisoformat(str(last_value))
        except ValueError:
            return True
        if not last_dt.tzinfo:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        return now - last_dt >= timedelta(days=interval_days)

    def _rotate_refresh_token(self, config: ConnectorConfig, provider: str, now: datetime) -> None:
        if provider == "azure_automation":
            if self._trigger_automation(config.connector_id, "refresh_token"):
                self._stamp_rotation(config, "last_refresh_token_rotated_at", now)
            return
        if self._refresh_connector_tokens(config):
            self._stamp_rotation(config, "last_refresh_token_rotated_at", now)

    def _rotate_client_secret(self, config: ConnectorConfig, provider: str, now: datetime) -> None:
        if provider == "azure_automation":
            if self._trigger_automation(config.connector_id, "client_secret"):
                self._stamp_rotation(config, "last_client_secret_rotated_at", now)
            return
        if self._trigger_automation(config.connector_id, "client_secret"):
            self._stamp_rotation(config, "last_client_secret_rotated_at", now)

    def _refresh_connector_tokens(self, config: ConnectorConfig) -> bool:
        connector_cls = get_connector_class(config.connector_id)
        if not connector_cls:
            logger.warning(
                "rotation_missing_connector_class", extra={"connector_id": config.connector_id}
            )
            return False
        try:
            connector = connector_cls(config)
            refresh = getattr(connector, "refresh_tokens", None)
            if callable(refresh):
                refresh()
                return True
            logger.warning(
                "rotation_missing_refresh_hook",
                extra={"connector_id": config.connector_id},
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception(
                "rotation_refresh_failed",
                extra={"connector_id": config.connector_id, "error": str(exc)},
            )
        return False

    def _trigger_automation(self, connector_id: str, secret_type: str) -> bool:
        webhook_url = self._automation_webhook_url
        if not webhook_url:
            logger.warning(
                "rotation_missing_webhook",
                extra={"connector_id": connector_id, "secret_type": secret_type},
            )
            return False
        payload = {
            "connector_id": connector_id,
            "secret_type": secret_type,
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            response = httpx.post(webhook_url, json=payload, timeout=10.0)
            if response.status_code >= 300:
                logger.warning(
                    "rotation_webhook_failed",
                    extra={
                        "connector_id": connector_id,
                        "secret_type": secret_type,
                        "status": response.status_code,
                        "body": response.text,
                    },
                )
                return False
            return True
        except httpx.HTTPError as exc:
            logger.warning(
                "rotation_webhook_error",
                extra={"connector_id": connector_id, "secret_type": secret_type, "error": str(exc)},
            )
            return False

    def _stamp_rotation(self, config: ConnectorConfig, key: str, now: datetime) -> None:
        config.custom_fields = config.custom_fields or {}
        config.custom_fields[key] = now.isoformat()
        self._store.save(config)
