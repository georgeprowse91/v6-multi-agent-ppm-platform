# Orchestration Service

Central multi-agent coordinator used by the API gateway. The orchestrator loads agent
implementations and exposes routing through the API.

## Current state

- Orchestrator is implemented as a Python module (`apps/orchestration-service/src/orchestrator.py`).
- It is invoked by the API gateway at startup; there is no standalone HTTP server yet.

## Quickstart

Run the API gateway, which bootstraps the orchestrator:

```bash
make run-api
```

## How to verify

```bash
curl http://localhost:8000/api/v1/status
```

Expected response includes:

```json
{"status":"healthy","orchestrator_initialized":true,"agents_loaded":25}
```

## Key files

- `apps/orchestration-service/src/orchestrator.py`: agent lifecycle manager.
- `agents/**/src/*.py`: agent implementations loaded by the orchestrator.
- `apps/orchestration-service/policies/bundles/default-policy-bundle.yaml`: default policy bundle path.

## Example usage (Python)

```python
from orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator()
```

## Next steps

- Add a dedicated HTTP service wrapper in `apps/orchestration-service/src/` if this becomes a
  standalone service.
- Move agent lifecycle status into a dedicated persistence layer (see `services/telemetry-service/`).
