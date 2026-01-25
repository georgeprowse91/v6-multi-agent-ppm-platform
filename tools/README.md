# Developer Tooling

This folder houses repo-aware tooling for formatting, linting, code generation, and local
development workflows. The scripts here reflect the current layout of `apps/`, `services/`,
`agents/`, `connectors/`, and `packages/`.

## Subfolders

| Folder | Purpose |
| --- | --- |
| `codegen/` | OpenAPI validation and deterministic outputs for API contracts. |
| `format/` | Formatting entrypoints for Python sources in the repo. |
| `lint/` | Lint checks that mirror CI expectations. |
| `local-dev/` | Local Docker Compose helpers and environment notes. |

## Commands to run

### Format all
```bash
python -m tools.format.run
```

### Lint all
```bash
python -m tools.lint.run
```

### Run local dev stack
```bash
bash tools/local-dev/dev_up.sh
```

### Run a single agent locally
```bash
python -m tools.agent_runner run-agent --name agent-10-schedule-planning
```

### Run a connector locally (validation-only)
```bash
python -m tools.connector_runner run-connector --name jira --dry-run
```

### Run codegen (OpenAPI)
```bash
python -m tools.codegen.run
```

The codegen step validates `docs/api/openapi.yaml` and writes a deterministic summary to
`apps/api-gateway/openapi/`.

## CI / pre-commit integration

* CI relies on `make lint`, `make format`, and `make codegen`. The Makefile now delegates to
  the scripts in this folder for consistent behavior.
* If you install `pre-commit` manually, you can add hooks that call these commands, but this
  repo currently runs them via Make targets.

## Troubleshooting

* **`python -m tools.lint.run` fails with “command not found”**: install dev dependencies
  via `pip install -e .[dev]`.
* **`run-agent` fails with “No Python entrypoint found”**: add a module under
  `agents/<domain>/<agent-name>/src/` or provide `--docker` if the agent is containerized.
* **`run-connector` fails validation**: open the connector’s `manifest.yaml` and ensure it
  defines `id` and `version`, plus a `mappings/` directory.
* **Docker compose fails to start**: confirm `.env` is populated (see `.env.example`) and
  that Docker Desktop is running.
