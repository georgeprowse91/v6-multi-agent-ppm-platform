# Agent 16: Compliance Regulatory Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 16: Compliance Regulatory. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- [src](/agents/delivery-management/agent-16-compliance-regulatory/src): Implementation source for this component.
- [tests](/agents/delivery-management/agent-16-compliance-regulatory/tests): Test suites and fixtures.
- [Dockerfile](/agents/delivery-management/agent-16-compliance-regulatory/Dockerfile): Container build recipe for local or CI use.
- [COMPLIANCE_CONTROL_CATALOG.md](/agents/delivery-management/agent-16-compliance-regulatory/COMPLIANCE_CONTROL_CATALOG.md): Scope validation, control catalog, and handoff boundaries for execution readiness.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-16-compliance-regulatory --dry-run
```

Run unit tests (if present):

```bash
pytest agents/delivery-management/agent-16-compliance-regulatory/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
