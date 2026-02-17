# Observability Package

## Purpose

Describe the Observability shared package and how it supports platform services.

## What's inside

- [src](/packages/observability/src): Implementation source for this component.

## How it's used

Packages are imported by apps, services, and agents across the repository.

## How to run / develop / test

Run unit tests (if present) or import modules in a Python shell:

```bash
pytest packages/observability
```

## Configuration

Shared packages rely on repository-wide configuration in `.env` when needed.

## Troubleshooting

- Import errors: ensure the package is installed in editable mode (`make install-dev`).
- Missing dependencies: check `pyproject.toml` for required extras.

## Cost tracking metrics

The observability package now exposes two OpenTelemetry counters for runtime cost monitoring:

- `llm_tokens_consumed`: records request/response token volumes for LLM calls.
- `external_api_cost`: records estimated AUD cost for connector and external API calls.

Use `build_cost_metrics(service_name)` to create these counters and record usage attributes such as
`agent_id`, `connector_name`, `model`, and `token_type`.

## Telemetry standard contract

The shared telemetry contract in `observability.telemetry` standardizes dimensions and baseline metrics:

- Required dimensions/tags for emitted metrics: `service.name`, `tenant.id`, `trace.id`.
- HTTP golden signals metrics: `http_requests_total`, `http_request_duration_seconds`, `http_request_errors_total`, `http_requests_in_flight`.
- Domain workflow metrics: `orchestrator_executions_total`, `orchestrator_execution_duration_seconds`,
  `workflow_executions_total`, `workflow_execution_duration_seconds`,
  `connector_sync_executions_total`, `connector_sync_execution_duration_seconds`.

Use `build_business_workflow_metrics(service_name, workflow)` to instrument workflow-level business outcomes with consistent tags.
