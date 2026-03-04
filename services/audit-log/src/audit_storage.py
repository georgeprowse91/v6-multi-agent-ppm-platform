from __future__ import annotations

import base64
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast

from azure.core.exceptions import HttpResponseError, ResourceModifiedError
from azure.storage.blob import BlobServiceClient
from cryptography.fernet import Fernet, InvalidToken
from security.secrets import resolve_secret


class WORMStorageError(RuntimeError):
    pass


logger = logging.getLogger(__name__)


@dataclass
class AuditRetentionPolicy:
    policy_id: str
    duration_days: int


class WORMStorage(ABC):
    @abstractmethod
    def persist_event(
        self, event_id: str, payload: dict[str, Any], retention: AuditRetentionPolicy
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def fetch_event(self, event_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def list_events(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def prune_expired(self, now: datetime | None = None) -> int:
        raise NotImplementedError

    @abstractmethod
    def ping(self) -> None:
        raise NotImplementedError


class LocalEncryptedWORMStorage(WORMStorage):
    def __init__(self, root: Path, encryption_key: str) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.fernet = Fernet(encryption_key.encode("utf-8"))

    def _event_path(self, event_id: str) -> Path:
        return self.root / f"{event_id}.json.enc"

    def persist_event(
        self, event_id: str, payload: dict[str, Any], retention: AuditRetentionPolicy
    ) -> None:
        path = self._event_path(event_id)
        if path.exists():
            raise WORMStorageError("Immutable store already contains event")

        payload = {
            **payload,
            "retention_policy": retention.policy_id,
            "retention_until": (
                datetime.now(timezone.utc) + timedelta(days=retention.duration_days)
            ).isoformat(),
        }
        encrypted = self.fernet.encrypt(json.dumps(payload).encode("utf-8"))
        with open(path, "xb") as handle:
            handle.write(encrypted)

    def fetch_event(self, event_id: str) -> dict[str, Any] | None:
        path = self._event_path(event_id)
        if not path.exists():
            return None
        decrypted = self.fernet.decrypt(path.read_bytes())
        return cast(dict[str, Any], json.loads(decrypted))

    def list_events(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for path in self.root.glob("*.json.enc"):
            try:
                decrypted = self.fernet.decrypt(path.read_bytes())
                events.append(cast(dict[str, Any], json.loads(decrypted)))
            except (InvalidToken, OSError, json.JSONDecodeError):
                continue
        return events

    def prune_expired(self, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        deleted = 0
        for path in self.root.glob("*.json.enc"):
            try:
                decrypted = self.fernet.decrypt(path.read_bytes())
                payload = cast(dict[str, Any], json.loads(decrypted))
                retention_until = payload.get("retention_until")
                if not retention_until:
                    continue
                cutoff = datetime.fromisoformat(retention_until)
                if cutoff.tzinfo is None:
                    cutoff = cutoff.replace(tzinfo=timezone.utc)
                if cutoff <= now:
                    path.unlink()
                    deleted += 1
            except (InvalidToken, OSError, json.JSONDecodeError):
                continue
        return deleted

    def ping(self) -> None:
        if not self.root.exists():
            raise WORMStorageError("Local WORM storage root missing")


class AzureBlobWORMStorage(WORMStorage):
    def __init__(self, connection_string: str, container: str) -> None:
        self.client = BlobServiceClient.from_connection_string(connection_string)
        self.container = container
        self._ensure_container()

    def _ensure_container(self) -> None:
        container_client = self.client.get_container_client(self.container)
        if not container_client.exists():
            container_client.create_container()
            container_client.set_container_access_policy(signed_identifiers={})

    def persist_event(
        self, event_id: str, payload: dict[str, Any], retention: AuditRetentionPolicy
    ) -> None:
        container_client = self.client.get_container_client(self.container)
        blob_client = container_client.get_blob_client(f"{event_id}.json")
        if blob_client.exists():
            raise WORMStorageError("Immutable store already contains event")
        payload["retention_policy"] = retention.policy_id
        payload["retention_until"] = (
            datetime.now(timezone.utc) + timedelta(days=retention.duration_days)
        ).isoformat()
        try:
            blob_client.upload_blob(json.dumps(payload), overwrite=False)
        except HttpResponseError as exc:
            raise WORMStorageError("Failed to persist audit event to immutable storage") from exc

    def fetch_event(self, event_id: str) -> dict[str, Any] | None:
        blob_client = self.client.get_blob_client(self.container, f"{event_id}.json")
        if not blob_client.exists():
            return None
        data = blob_client.download_blob().readall()
        return cast(dict[str, Any], json.loads(data))

    def list_events(self) -> list[dict[str, Any]]:
        container_client = self.client.get_container_client(self.container)
        events: list[dict[str, Any]] = []
        for blob in container_client.list_blobs():
            data = container_client.get_blob_client(blob.name).download_blob().readall()
            events.append(cast(dict[str, Any], json.loads(data)))
        return events

    def prune_expired(self, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        deleted = 0
        container_client = self.client.get_container_client(self.container)
        for blob in container_client.list_blobs():
            blob_client = container_client.get_blob_client(blob.name)
            payload = json.loads(blob_client.download_blob().readall())
            retention_until = payload.get("retention_until")
            if not retention_until:
                continue
            cutoff = datetime.fromisoformat(retention_until)
            if cutoff.tzinfo is None:
                cutoff = cutoff.replace(tzinfo=timezone.utc)
            if cutoff <= now:
                try:
                    blob_client.delete_blob()
                    deleted += 1
                except ResourceModifiedError:
                    logger.warning("immutable_blob_retention_locked", extra={"blob": blob.name})
                except HttpResponseError as exc:
                    logger.warning(
                        "immutable_blob_delete_failed",
                        extra={"blob": blob.name, "error": str(exc)},
                    )
        return deleted

    def ping(self) -> None:
        container_client = self.client.get_container_client(self.container)
        if not container_client.exists():
            raise WORMStorageError("Azure WORM container missing")


def get_worm_storage() -> WORMStorage:
    connection = resolve_secret(os.getenv("AUDIT_WORM_CONNECTION_STRING"))
    container = os.getenv("AUDIT_WORM_CONTAINER", "audit-events")
    encryption_key = resolve_secret(os.getenv("AUDIT_LOG_ENCRYPTION_KEY"))
    if connection:
        return AzureBlobWORMStorage(connection, container)
    if not encryption_key:
        encryption_key = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")
    root = Path(os.getenv("AUDIT_WORM_LOCAL_PATH", "services/audit-log/storage/immutable"))
    return LocalEncryptedWORMStorage(root=root, encryption_key=encryption_key)
