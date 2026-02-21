# Telemetry Service endpoint reference

Source: `services/telemetry-service/src/main.py`

| Method | Path | Handler |
| --- | --- | --- |
| `GET` | `/healthz` | `healthz` |
| `POST` | `/v1/telemetry/ingest` | `ingest` |
| `GET` | `/version` | `version` |
