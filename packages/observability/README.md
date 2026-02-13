# Observability Package

## Purpose

Describe the Observability shared package and how it supports platform services.

## What's inside

- `packages/observability/src`: Implementation source for this component.

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
