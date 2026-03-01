# IoT Connector Specification

**Purpose:** Specify the IoT connector's protocols, configuration schema, data normalisation model, and usage instructions.
**Audience:** Integration engineers, DevOps, and solution architects connecting IoT/OT telemetry to the platform.
**Owner:** Integration Engineering
**Last reviewed:** 2026-02-20
**Related docs:** [../platform-architecture-overview.md](../platform-architecture-overview.md) · [../agent-system-design.md](../agent-system-design.md) · [../../../solution-index.md](../../../solution-index.md)

> **Migration note:** Renamed and moved from `connectors/iot.md` on 2026-02-20 to place connector specifications within the solution design domain.

---

# IoT Connector

## Overview
The IoT connector ingests telemetry from custom hardware devices and normalizes sensor readings into the platform’s canonical data model. It supports HTTP polling and MQTT streaming to accommodate different device communication patterns.

## Supported protocols
- **HTTP/HTTPS**: Poll device APIs for sensor data and device metadata.
- **MQTT**: Subscribe to topics for real-time sensor updates and publish command payloads.

## Configuration
Configure the connector using connector settings or environment variables.

### Required settings (HTTP)
| Field | Description |
| --- | --- |
| `device_endpoint` | Base URL for the device API (e.g., `https://iot.example.com`). |
| `auth_token` | Bearer token used to authenticate HTTP requests. |
| `protocol` | Set to `http` or `https`. |

### Required settings (MQTT)
| Field | Description |
| --- | --- |
| `mqtt_broker` | Hostname or IP of the MQTT broker. |
| `mqtt_port` | Port for the broker (default: 1883). |
| `protocol` | Set to `mqtt`. |

### Optional settings
| Field | Description |
| --- | --- |
| `device_ids` | Comma-separated list of device IDs to filter polling. |
| `sensor_types` | Comma-separated list of sensor types to filter polling. |
| `mqtt_username` / `mqtt_password` | MQTT authentication credentials. |
| `mqtt_topic` | MQTT topic for subscribing/publishing (default: `devices/+/sensors`). |
| `poll_interval_seconds` | Polling interval for HTTP reads (default: 30 seconds). |

### Environment variables
- `IOT_PROTOCOL`
- `IOT_DEVICE_ENDPOINT`
- `IOT_AUTH_TOKEN`
- `IOT_DEVICE_IDS`
- `IOT_SENSOR_TYPES`
- `IOT_MQTT_BROKER`
- `IOT_MQTT_PORT`
- `IOT_MQTT_USERNAME`
- `IOT_MQTT_PASSWORD`
- `IOT_MQTT_TOPIC`
- `IOT_POLL_INTERVAL_SECONDS`

## Data normalization
Incoming sensor payloads are normalized into the following fields:

| Field | Description |
| --- | --- |
| `device_id` | Device identifier for the sensor reading. |
| `sensor_type` | Type of sensor (e.g., temperature, vibration). |
| `value` | Sensor value or measurement. |
| `unit` | Measurement unit (e.g., °C, psi). |
| `observed_at` | Timestamp of the reading. |
| `metadata` | Any additional payload attributes. |

## Usage
1. Create a connector configuration and set the protocol-specific fields.
2. Test the connection using the API to validate device connectivity.
3. Enable the connector to begin polling or streaming data.

### Example payload (HTTP)
```json
{
  "deviceId": "device-1",
  "sensorType": "temperature",
  "measurement": 72.5,
  "units": "F",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Example normalized output
```json
{
  "source": "iot",
  "device_id": "device-1",
  "sensor_type": "temperature",
  "value": 72.5,
  "unit": "F",
  "observed_at": "2024-01-01T00:00:00Z",
  "metadata": {}
}
```
