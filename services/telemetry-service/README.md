# Telemetry Service

The telemetry service ingests structured log/metric/trace payloads and writes them to a local
JSONL store in dev mode. It is designed to align with the observability standards defined in
`docs/architecture/observability-architecture.md`.

## Contracts

- OpenAPI: `services/telemetry-service/contracts/openapi.yaml`

## Run locally

```bash
python -m tools.component_runner run --type service --name telemetry-service
```

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `TELEMETRY_STORAGE_PATH` | `services/telemetry-service/pipelines/telemetry.jsonl` | JSONL storage file for ingested telemetry |
| `LOG_LEVEL` | `info` | Logging verbosity |
| `PORT` | `8080` | HTTP port for the service |

## Example request

```bash
curl -X POST http://localhost:8080/telemetry/ingest \
  -H "Content-Type: application/json" \
  -d '{"source": "api-gateway", "type": "log", "payload": {"message": "hello"}}'
```

## Tests

```bash
pytest services/telemetry-service/tests
```
