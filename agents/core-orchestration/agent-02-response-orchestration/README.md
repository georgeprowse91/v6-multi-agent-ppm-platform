# Agent 02: Response Orchestration Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 02: Response Orchestration. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Scope and responsibilities

Agent 02 is responsible for executing the multi-agent plan created by the intent router, coordinating parallel/sequential agent execution, and aggregating responses into a single payload for the caller. It owns orchestration-specific behaviors such as retry logic, caching, circuit breaking, and audit event emission. It does **not** decide which intents/agents to run, nor does it enforce approval policies beyond invoking downstream agents that require approvals.

### Inputs

Agent 02 accepts an orchestration request with:

- `routing`: ordered routing entries (agent id, optional action, dependencies).
- `parameters`: shared parameters for downstream agents (including optional `prompt` metadata).
- `query`: original user query (informational).
- `context`: tenant/correlation metadata and project context.
- `correlation_id`, `tenant_id`, `prompt_id`, `prompt_description`, `prompt_tags`: optional prompt context when not already embedded in `parameters.prompt`.

### Outputs

Agent 02 returns:

- `aggregated_response`: merged text output from successful agent calls.
- `agent_results`: per-agent status and payloads (success/failure, cached status).
- `execution_summary`: counts of total/successful/failed agents.

### Decisions owned by Agent 02

- Execution grouping derived from dependencies (parallel vs sequential).
- Retry/backoff policy for each agent invocation.
- Circuit breaker state and cache usage.
- Aggregation behavior when partial failures occur.
- Optional external research enrichment when prompt metadata indicates vendor/compliance needs.

### Must / must-not behaviors

Must:
- Honor dependency ordering in routing entries.
- Preserve correlation/tenant metadata when invoking downstream agents.
- Emit audit events for invocations, failures, and aggregation.
- Respect configured timeouts, retries, and concurrency limits.

Must not:
- Re-route or reinterpret intents (owned by Agent 01).
- Initiate approval workflows directly (owned by Agent 03).
- Override downstream agent responses beyond aggregation and lightweight summarization.

## Orchestration flow + dependency map entry

**Flow:** `Agent 01 (Intent Router) → Agent 02 (Response Orchestration) → Downstream Agents → Aggregated Response`

**Dependencies:**
- Upstream: Agent 01 provides `routing` entries and shared parameters.
- Downstream: Specialized agents execute tasks; Agent 03 is invoked only if the routing plan includes approval-specific agents/actions.
- Shared services: event bus (publish `agent.requested`, `agent.completed`, `agent.failed`), audit logging, and observability metrics.

**Handoff boundaries:**
- Agent 01 hands off the routing plan and parameters; Agent 02 executes exactly what is provided and returns results + summary.
- Agent 03 owns approval gating and state transitions; Agent 02 only invokes the approval agent when included in routing.

## Overlap / leakage considerations

- **Routing vs orchestration:** Agent 02 should not choose or reorder intents; if it receives empty or cyclic routing, it must return an error (cycle detection) rather than attempt to infer intent.
- **Approval workflows:** Agent 02 should not implement approval logic itself; ensure the routing plan includes the approval agent for guarded actions.
- **Prompt enrichment:** Agent 02 enriches parameters with external research based on prompt metadata; prompt ownership remains with prompt templates and Agent 01 configuration.

## Gaps, inconsistencies, and alignment needs

- **Prompt metadata alignment:** Ensure prompt templates and UI inputs supply `prompt_id`, `prompt_description`, and `prompt_tags` consistently so external research behavior is deterministic.
- **Routing contract:** `depends_on` should be validated upstream in Agent 01 and/or `config/agents/intent-routing.yaml` to avoid runtime dependency cycles.
- **Connector alignment:** Downstream agents that require approval should expose explicit actions so the routing plan can include Agent 03 prior to execution.
- **UI/UX alignment:** Surface partial-failure aggregation messaging to users so they understand which agents succeeded vs failed.

## What's inside

- [src](/agents/core-orchestration/agent-02-response-orchestration/src): Implementation source for this component.
- [tests](/agents/core-orchestration/agent-02-response-orchestration/tests): Test suites and fixtures.
- [Dockerfile](/agents/core-orchestration/agent-02-response-orchestration/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-02-response-orchestration --dry-run
```

Run unit tests (if present):

```bash
pytest agents/core-orchestration/agent-02-response-orchestration/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
