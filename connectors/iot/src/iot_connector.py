"""
IoT Connector Implementation

Supports connecting to custom hardware devices over HTTP or MQTT to ingest
sensor telemetry data.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

_REPO_ROOT = Path(__file__).resolve().parents[4]
_COMMON_SRC = _REPO_ROOT / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(_REPO_ROOT)

from base_connector import (  # noqa: E402
    BaseConnector,
    ConnectionStatus,
    ConnectionTestResult,
    ConnectorCategory,
    ConnectorConfig,
)
from http_client import HttpClient, HttpClientError, RetryConfig  # noqa: E402
from connector_secrets import resolve_secret  # noqa: E402

import importlib
import importlib.util

_PAHO_SPEC = importlib.util.find_spec("paho")
_MQTT_SPEC = importlib.util.find_spec("paho.mqtt.client") if _PAHO_SPEC else None
mqtt = importlib.import_module("paho.mqtt.client") if _MQTT_SPEC else None


class IoTConnector(BaseConnector):
    """Connector for ingesting IoT sensor data."""

    CONNECTOR_ID = "iot"
    CONNECTOR_NAME = "IoT Integrations"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.IOT
    SUPPORTS_WRITE = True

    ENDPOINT_ENV = "IOT_DEVICE_ENDPOINT"
    AUTH_TOKEN_ENV = "IOT_AUTH_TOKEN"
    SENSOR_TYPES_ENV = "IOT_SENSOR_TYPES"
    DEVICE_IDS_ENV = "IOT_DEVICE_IDS"
    PROTOCOL_ENV = "IOT_PROTOCOL"
    MQTT_BROKER_ENV = "IOT_MQTT_BROKER"
    MQTT_PORT_ENV = "IOT_MQTT_PORT"
    MQTT_USERNAME_ENV = "IOT_MQTT_USERNAME"
    MQTT_PASSWORD_ENV = "IOT_MQTT_PASSWORD"
    MQTT_TOPIC_ENV = "IOT_MQTT_TOPIC"
    POLL_INTERVAL_ENV = "IOT_POLL_INTERVAL_SECONDS"

    HTTP_HEALTH_ENDPOINT = "/health"

    RESOURCE_PATHS = {
        "sensor_data": {
            "path": "/sensors/data",
            "items_path": "items",
            "write_method": "POST",
        },
        "devices": {
            "path": "/devices",
            "items_path": "items",
        },
        "commands": {
            "path": "/commands",
            "write_method": "POST",
        },
    }

    def __init__(
        self,
        config: ConnectorConfig,
        *,
        client: HttpClient | None = None,
        transport: Any | None = None,
        mqtt_client: Any | None = None,
    ) -> None:
        super().__init__(config)
        self._client = client
        self._transport = transport
        self._mqtt_client = mqtt_client

    def _get_protocol(self) -> str:
        protocol = resolve_secret(os.getenv(self.PROTOCOL_ENV))
        if not protocol:
            protocol = str(self.config.custom_fields.get("protocol", "http")).strip()
        protocol = protocol.lower()
        if protocol not in {"http", "https", "mqtt"}:
            raise ValueError("Unsupported protocol. Use http, https, or mqtt.")
        return protocol

    def _get_endpoint(self) -> str:
        endpoint = resolve_secret(os.getenv(self.ENDPOINT_ENV))
        if not endpoint:
            endpoint = self.config.instance_url
        if not endpoint:
            endpoint = str(self.config.custom_fields.get("device_endpoint", "")).strip()
        if not endpoint:
            raise ValueError(f"{self.ENDPOINT_ENV} environment variable is required")
        return endpoint.rstrip("/")

    def _get_auth_token(self) -> str:
        token = resolve_secret(os.getenv(self.AUTH_TOKEN_ENV))
        if not token:
            token = str(self.config.custom_fields.get("auth_token", "")).strip()
        if not token:
            raise ValueError(f"{self.AUTH_TOKEN_ENV} environment variable is required")
        return token

    def _get_sensor_types(self) -> list[str]:
        raw = resolve_secret(os.getenv(self.SENSOR_TYPES_ENV))
        if not raw:
            raw = self.config.custom_fields.get("sensor_types", "")
        return self._split_csv(raw)

    def _get_device_ids(self) -> list[str]:
        raw = resolve_secret(os.getenv(self.DEVICE_IDS_ENV))
        if not raw:
            raw = self.config.custom_fields.get("device_ids", "")
        if isinstance(raw, list):
            return [str(item).strip() for item in raw if str(item).strip()]
        return self._split_csv(raw)

    def _get_poll_interval(self) -> float:
        raw = resolve_secret(os.getenv(self.POLL_INTERVAL_ENV))
        if not raw:
            raw = self.config.custom_fields.get("poll_interval_seconds", 30)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 30.0

    def _get_mqtt_settings(self) -> dict[str, Any]:
        broker = resolve_secret(os.getenv(self.MQTT_BROKER_ENV))
        if not broker:
            broker = self.config.custom_fields.get("mqtt_broker")
        port = resolve_secret(os.getenv(self.MQTT_PORT_ENV))
        if not port:
            port = self.config.custom_fields.get("mqtt_port", 1883)
        username = resolve_secret(os.getenv(self.MQTT_USERNAME_ENV))
        if not username:
            username = self.config.custom_fields.get("mqtt_username")
        password = resolve_secret(os.getenv(self.MQTT_PASSWORD_ENV))
        if not password:
            password = self.config.custom_fields.get("mqtt_password")
        topic = resolve_secret(os.getenv(self.MQTT_TOPIC_ENV))
        if not topic:
            topic = self.config.custom_fields.get("mqtt_topic", "devices/+/sensors")
        return {
            "broker": broker,
            "port": int(port) if port else 1883,
            "username": username,
            "password": password,
            "topic": topic,
        }

    def _validate_config(self) -> None:
        protocol = self._get_protocol()
        if protocol in {"http", "https"}:
            _ = self._get_endpoint()
            _ = self._get_auth_token()
        if protocol == "mqtt":
            settings = self._get_mqtt_settings()
            if not settings.get("broker"):
                raise ValueError("MQTT broker is required for mqtt protocol")

    @staticmethod
    def _split_csv(raw: Any) -> list[str]:
        if not raw:
            return []
        return [item.strip() for item in str(raw).split(",") if item.strip()]

    def _build_http_client(self) -> HttpClient:
        if self._client:
            return self._client
        endpoint = self._get_endpoint()
        token = self._get_auth_token()
        retry_config = RetryConfig(
            max_retries=3,
            backoff_factor=0.5,
            retry_statuses=(429, 500, 502, 503, 504),
        )
        self._client = HttpClient(
            base_url=endpoint,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
            timeout=20.0,
            retry_config=retry_config,
            transport=self._transport,
        )
        return self._client

    def _build_mqtt_client(self) -> Any:
        if self._mqtt_client:
            return self._mqtt_client
        if mqtt is None:
            raise ValueError("MQTT client library not available. Install paho-mqtt.")
        client = mqtt.Client()
        settings = self._get_mqtt_settings()
        if settings.get("username"):
            client.username_pw_set(settings["username"], settings.get("password"))
        self._mqtt_client = client
        return client

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        client = self._build_http_client()
        return client.request(method, path, **kwargs)

    def authenticate(self) -> bool:
        try:
            self._validate_config()
        except ValueError:
            self._authenticated = False
            return False
        protocol = self._get_protocol()
        if protocol in {"http", "https"}:
            try:
                response = self._request("GET", self.HTTP_HEALTH_ENDPOINT)
                self._authenticated = response.status_code == 200
                return self._authenticated
            except (HttpClientError, ValueError):
                self._authenticated = False
                return False
        try:
            client = self._build_mqtt_client()
            settings = self._get_mqtt_settings()
            result = client.connect(settings["broker"], settings["port"])
            self._authenticated = result == 0
            return self._authenticated
        except Exception:
            self._authenticated = False
            return False

    def test_connection(self) -> ConnectionTestResult:
        try:
            self._validate_config()
        except ValueError as exc:
            return ConnectionTestResult(
                status=ConnectionStatus.INVALID_CONFIG,
                message=str(exc),
            )
        protocol = self._get_protocol()
        if protocol in {"http", "https"}:
            try:
                response = self._request("GET", self.HTTP_HEALTH_ENDPOINT)
                if response.status_code == 401:
                    return ConnectionTestResult(
                        status=ConnectionStatus.UNAUTHORIZED,
                        message="Invalid credentials. Please verify connector settings.",
                    )
                if response.status_code != 200:
                    return ConnectionTestResult(
                        status=ConnectionStatus.FAILED,
                        message=(
                            "IoT endpoint returned unexpected status: "
                            f"{response.status_code}"
                        ),
                        details={"status_code": response.status_code},
                    )
                self._authenticated = True
                return ConnectionTestResult(
                    status=ConnectionStatus.CONNECTED,
                    message="Successfully connected",
                )
            except HttpClientError as exc:
                if exc.status_code == 401:
                    return ConnectionTestResult(
                        status=ConnectionStatus.UNAUTHORIZED,
                        message="Invalid credentials. Please verify connector settings.",
                    )
                if exc.status_code is None:
                    return ConnectionTestResult(
                        status=ConnectionStatus.TIMEOUT,
                        message="Connection timed out while reaching the IoT endpoint.",
                    )
                return ConnectionTestResult(
                    status=ConnectionStatus.FAILED,
                    message=f"Connection failed: {exc.message}",
                    details={"status_code": exc.status_code},
                )
            except Exception as exc:  # pragma: no cover - defensive
                return ConnectionTestResult(
                    status=ConnectionStatus.FAILED,
                    message=f"Unexpected error: {exc}",
                )
        try:
            client = self._build_mqtt_client()
            settings = self._get_mqtt_settings()
            result = client.connect(settings["broker"], settings["port"])
            if result != 0:
                return ConnectionTestResult(
                    status=ConnectionStatus.FAILED,
                    message="Failed to connect to MQTT broker",
                    details={"result_code": result},
                )
            self._authenticated = True
            return ConnectionTestResult(
                status=ConnectionStatus.CONNECTED,
                message="Successfully connected to MQTT broker",
            )
        except Exception as exc:
            return ConnectionTestResult(
                status=ConnectionStatus.FAILED,
                message=f"Connection failed: {exc}",
            )

    def ingest_sensor_data(self, payload: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        records = []
        for entry in payload:
            records.append(self._normalize_sensor_record(entry))
        return records

    def _normalize_sensor_record(self, record: dict[str, Any]) -> dict[str, Any]:
        device_id = record.get("device_id") or record.get("deviceId") or record.get("device")
        if not device_id:
            device_ids = self._get_device_ids()
            device_id = device_ids[0] if device_ids else "unknown"
        sensor_type = (
            record.get("sensor_type")
            or record.get("sensorType")
            or record.get("type")
            or record.get("metric")
        )
        observed_at = (
            record.get("observed_at")
            or record.get("timestamp")
            or record.get("time")
            or datetime.now(timezone.utc).isoformat()
        )
        value = record.get("value")
        if value is None:
            value = record.get("reading") or record.get("measurement")
        unit = record.get("unit") or record.get("units")
        metadata = {
            key: value
            for key, value in record.items()
            if key
            not in {
                "device_id",
                "deviceId",
                "device",
                "sensor_type",
                "sensorType",
                "type",
                "metric",
                "observed_at",
                "timestamp",
                "time",
                "value",
                "reading",
                "measurement",
                "unit",
                "units",
            }
        }
        return {
            "source": self.CONNECTOR_ID,
            "device_id": device_id,
            "sensor_type": sensor_type,
            "value": value,
            "unit": unit,
            "observed_at": observed_at,
            "metadata": metadata,
        }

    def poll_sensor_data(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return self.read("sensor_data", filters=filters, limit=limit, offset=offset)

    def stream_sensor_data(self, iterations: int = 1) -> Iterable[list[dict[str, Any]]]:
        for _ in range(iterations):
            yield self.poll_sensor_data()

    def read(
        self,
        resource_type: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if not self._authenticated and not self.authenticate():
            raise RuntimeError("Failed to authenticate with IoT endpoint")
        if resource_type not in self.RESOURCE_PATHS:
            raise ValueError(f"Unsupported resource type: {resource_type}")
        protocol = self._get_protocol()
        if protocol == "mqtt":
            return self._read_from_mqtt(resource_type)
        info = self.RESOURCE_PATHS[resource_type]
        params = {"limit": limit, "offset": offset}
        merged_filters = dict(filters or {})
        if resource_type == "sensor_data":
            sensor_types = merged_filters.pop("sensor_types", None)
            if sensor_types is None:
                sensor_types = self._get_sensor_types()
            if isinstance(sensor_types, list):
                sensor_types = ",".join(sensor_types)
            if sensor_types:
                params["sensor_types"] = sensor_types
            device_ids = merged_filters.pop("device_ids", None)
            if device_ids is None:
                device_ids = self._get_device_ids()
            if isinstance(device_ids, list):
                device_ids = ",".join(device_ids)
            if device_ids:
                params["device_ids"] = device_ids
        params.update(merged_filters)
        response = self._request("GET", info["path"], params=params)
        data = response.json()
        items = self._extract_items(data, info.get("items_path"))
        if resource_type == "sensor_data":
            return self.ingest_sensor_data(items)
        return items

    def _extract_items(self, data: Any, items_path: str | None) -> list[dict[str, Any]]:
        if items_path:
            current: Any = data
            for key in items_path.split("."):
                if not isinstance(current, dict):
                    return []
                current = current.get(key, {})
            return current if isinstance(current, list) else []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            items = data.get("items")
            if isinstance(items, list):
                return items
            return [data]
        return []

    def _read_from_mqtt(self, resource_type: str) -> list[dict[str, Any]]:
        if resource_type != "sensor_data":
            raise ValueError("MQTT only supports sensor_data resource")
        client = self._build_mqtt_client()
        settings = self._get_mqtt_settings()
        messages: list[dict[str, Any]] = []
        if hasattr(client, "get_messages"):
            raw_messages = client.get_messages(settings["topic"])
            if isinstance(raw_messages, list):
                for raw in raw_messages:
                    if isinstance(raw, dict):
                        messages.append(raw)
                    elif isinstance(raw, str):
                        try:
                            messages.append(json.loads(raw))
                        except json.JSONDecodeError:
                            continue
        return self.ingest_sensor_data(messages)

    def write(self, resource_type: str, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.SUPPORTS_WRITE:
            raise NotImplementedError(
                f"{self.CONNECTOR_NAME} does not support write operations"
            )
        if not self._authenticated and not self.authenticate():
            raise RuntimeError("Failed to authenticate with IoT endpoint")
        protocol = self._get_protocol()
        if protocol == "mqtt":
            return self._write_to_mqtt(resource_type, data)
        if resource_type not in self.RESOURCE_PATHS:
            raise ValueError(f"Unsupported resource type: {resource_type}")
        info = self.RESOURCE_PATHS[resource_type]
        write_method = info.get("write_method")
        if not write_method:
            raise ValueError(f"Write not supported for resource: {resource_type}")
        response = self._request(write_method, info["path"], json=data)
        payload = response.json()
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            return payload.get("items", [payload]) if payload else []
        return []

    def _write_to_mqtt(self, resource_type: str, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if resource_type != "commands":
            raise ValueError("MQTT write only supports commands resource")
        client = self._build_mqtt_client()
        settings = self._get_mqtt_settings()
        topic = settings["topic"]
        for entry in data:
            client.publish(topic, json.dumps(entry))
        return data


def create_iot_connector(config: ConnectorConfig) -> IoTConnector:
    return IoTConnector(config)
