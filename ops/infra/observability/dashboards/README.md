# Dashboards Infrastructure

## Purpose

Document infrastructure resources under infra/observability/dashboards.

## What's inside

- [ppm-platform.json](/infra/observability/dashboards/ppm-platform.json): JSON data asset or configuration.
- [ppm-slo.json](/infra/observability/dashboards/ppm-slo.json): JSON data asset or configuration.
- [ppm-error-budget.json](/infra/observability/dashboards/ppm-error-budget.json): Error budget reporting dashboard.

## How it's used

These assets are referenced during deployment and operational runbooks.

## How to run / develop / test

Use Terraform/Helm/Kubernetes tooling referenced in this directory to apply changes.

## Configuration

Infrastructure configuration lives in the files within this folder and `.env` for local tooling.

## Troubleshooting

- Terraform errors: ensure the correct workspace/env variables are set.
- Kubernetes apply failures: verify cluster access and namespace settings.


## Standardized telemetry contract

Dashboards now align with the shared observability contract metrics:
`http_requests_total`, `http_request_duration_seconds`, `http_request_errors_total`,
`http_requests_in_flight`, `orchestrator_executions_total`, `workflow_executions_total`,
and `connector_sync_executions_total` (plus duration histograms).
