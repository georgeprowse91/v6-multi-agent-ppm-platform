from __future__ import annotations

import json
import logging
import os
import ssl
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("orchestration-service.leader-election")

SERVICE_ACCOUNT_TOKEN = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")
SERVICE_ACCOUNT_CA = Path("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")


@dataclass
class LeaderStatus:
    leader_id: str | None = None
    renew_time: float | None = None


class LeaderElector:
    def __init__(
        self,
        name: str,
        namespace: str,
        identity: str,
        lease_duration: int = 30,
        renew_deadline: int = 20,
        retry_period: int = 10,
        enabled: bool = False,
        fail_open: bool = True,
    ) -> None:
        self.name = name
        self.namespace = namespace
        self.identity = identity
        self.lease_duration = lease_duration
        self.renew_deadline = renew_deadline
        self.retry_period = retry_period
        self.enabled = enabled
        self.fail_open = fail_open
        self._is_leader = not enabled
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._status = LeaderStatus()

    @property
    def is_leader(self) -> bool:
        return self._is_leader

    @property
    def status(self) -> LeaderStatus:
        return self._status

    def start(self) -> None:
        if not self.enabled:
            self._is_leader = True
            return
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._elect()
            except Exception:
                logger.exception("leader_election_failed")
                if self.fail_open:
                    self._is_leader = True
                else:
                    self._is_leader = False
            self._stop_event.wait(self.retry_period)

    def _elect(self) -> None:
        if not self._kubernetes_available():
            logger.warning("leader_election_kubernetes_unavailable")
            self._is_leader = self.fail_open
            return
        configmap = self._get_configmap()
        now = time.time()
        if not configmap:
            created = self._create_configmap(now)
            self._is_leader = created
            return
        metadata = configmap.get("metadata", {})
        annotations = metadata.get("annotations", {})
        leader_id = annotations.get("leader-id")
        renew_time = float(annotations.get("renew-time", "0") or 0)
        expired = now - renew_time > self.lease_duration
        self._status = LeaderStatus(leader_id=leader_id, renew_time=renew_time)
        if leader_id == self.identity or expired:
            updated = self._update_configmap(metadata, now)
            self._is_leader = updated
            if updated:
                self._status = LeaderStatus(leader_id=self.identity, renew_time=now)
            return
        self._is_leader = False

    def _kubernetes_available(self) -> bool:
        return bool(
            os.getenv("KUBERNETES_SERVICE_HOST")
            and os.getenv("KUBERNETES_SERVICE_PORT")
            and SERVICE_ACCOUNT_TOKEN.exists()
            and SERVICE_ACCOUNT_CA.exists()
        )

    def _api_base(self) -> str:
        host = os.getenv("KUBERNETES_SERVICE_HOST")
        port = os.getenv("KUBERNETES_SERVICE_PORT")
        return f"https://{host}:{port}"

    def _headers(self) -> dict[str, str]:
        token = SERVICE_ACCOUNT_TOKEN.read_text().strip()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _ssl_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context(cafile=str(SERVICE_ACCOUNT_CA))
        return context

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict | None:
        url = f"{self._api_base()}{path}"
        data = json.dumps(payload).encode("utf-8") if payload else None
        request = urllib.request.Request(url, data=data, method=method, headers=self._headers())
        try:
            with urllib.request.urlopen(
                request, context=self._ssl_context(), timeout=5
            ) as response:
                if response.status == 204:
                    return None
                body = response.read().decode("utf-8")
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            logger.warning("leader_election_http_error", extra={"status": exc.code})
            return None

    def _get_configmap(self) -> dict | None:
        path = f"/api/v1/namespaces/{self.namespace}/configmaps/{self.name}"
        return self._request("GET", path)

    def _create_configmap(self, now: float) -> bool:
        body = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": self.name,
                "namespace": self.namespace,
                "annotations": {
                    "leader-id": self.identity,
                    "renew-time": str(now),
                },
            },
        }
        path = f"/api/v1/namespaces/{self.namespace}/configmaps"
        response = self._request("POST", path, body)
        return response is not None

    def _update_configmap(self, metadata: dict, now: float) -> bool:
        resource_version = metadata.get("resourceVersion")
        if not resource_version:
            return False
        body = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": self.name,
                "namespace": self.namespace,
                "resourceVersion": resource_version,
                "annotations": {
                    "leader-id": self.identity,
                    "renew-time": str(now),
                },
            },
        }
        path = f"/api/v1/namespaces/{self.namespace}/configmaps/{self.name}"
        response = self._request("PUT", path, body)
        return response is not None


def build_leader_elector(service_name: str) -> LeaderElector:
    enabled = os.getenv("LEADER_ELECTION_ENABLED", "false").lower() == "true"
    namespace = os.getenv("LEADER_ELECTION_NAMESPACE", "default")
    configmap_name = os.getenv("LEADER_ELECTION_CONFIGMAP", f"{service_name}-leader")
    identity = os.getenv("LEADER_ELECTION_ID", os.getenv("HOSTNAME", service_name))
    lease_duration = int(os.getenv("LEADER_ELECTION_LEASE_SECONDS", "30"))
    renew_deadline = int(os.getenv("LEADER_ELECTION_RENEW_SECONDS", "20"))
    retry_period = int(os.getenv("LEADER_ELECTION_RETRY_SECONDS", "10"))
    fail_open = os.getenv("LEADER_ELECTION_FAIL_OPEN", "true").lower() == "true"
    return LeaderElector(
        name=configmap_name,
        namespace=namespace,
        identity=identity,
        lease_duration=lease_duration,
        renew_deadline=renew_deadline,
        retry_period=retry_period,
        enabled=enabled,
        fail_open=fail_open,
    )
