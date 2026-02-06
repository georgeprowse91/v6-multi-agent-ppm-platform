# Packages

Shared packages imported by apps, services, and agents across the repository.

## Directory structure

| Folder | Description |
|--------|-------------|
| [canvas-engine/](./canvas-engine/) | Canvas rendering engine (TypeScript/React) for dashboards, timelines, and documents |
| [common/](./common/) | Common Python utilities (exceptions module) |
| [contracts/](./contracts/) | Service contracts and schema artifacts (auth, data, events, models) |
| [crypto/](./crypto/) | Cryptographic utilities |
| [data-quality/](./data-quality/) | Data quality rules, remediation, and schema validation |
| [event_bus/](./event_bus/) | Event bus with Azure Service Bus support |
| [feature-flags/](./feature-flags/) | Feature flag management |
| [llm/](./llm/) | LLM client, prompts, and CLI |
| [methodology-engine/](./methodology-engine/) | Project methodology engine |
| [observability/](./observability/) | Observability (metrics, logging, tracing, OpenTelemetry) |
| [policy/](./policy/) | Policy evaluation utilities |
| [security/](./security/) | Security package (auth, IAM, DLP, secrets, crypto, keyvault) |
| [testing/](./testing/) | Testing utilities |
| [ui-kit/](./ui-kit/) | UI kit components |
| [workflow/](./workflow/) | Workflow dispatchers, Celery tasks, and result aggregation |

## How it's used

Packages are imported by apps, services, and agents across the repository.

## How to run / develop / test

Run unit tests (if present) or import modules in a Python shell:

```bash
pytest packages
```

## Configuration

Shared packages rely on repository-wide configuration in `.env` when needed.

## Troubleshooting

- Import errors: ensure the package is installed in editable mode (`make install-dev`).
- Missing dependencies: check `pyproject.toml` for required extras.
