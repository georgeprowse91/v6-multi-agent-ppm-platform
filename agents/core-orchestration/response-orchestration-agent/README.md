# Response Orchestration Agent Specification

## Purpose

Define the responsibilities, workflows, and integration points for the Response Orchestration Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Intended scope

### Responsibilities
- Execute the multi-agent plan created by the intent router, coordinating parallel/sequential agent execution.
- Aggregate responses from multiple downstream agents into a single payload for the caller.
- Manage retry logic, caching, circuit breaking, and audit event emission for orchestration.
- Optionally enrich parameters with external research when prompt metadata indicates vendor/compliance needs.

### Inputs
- `routing`: ordered routing entries (agent id, optional action, dependencies).
- `parameters`: shared parameters for downstream agents (including optional `prompt` metadata).
- `query`: original user query (informational).
- `context`: tenant/correlation metadata and project context.
- `correlation_id`, `tenant_id`, `prompt_id`, `prompt_description`, `prompt_tags`: optional prompt context when not already embedded in `parameters.prompt`.

### Outputs
- `aggregated_response`: merged text output from successful agent calls.
- `agent_results`: per-agent status and payloads (success/failure, cached status).
- `execution_summary`: counts of total/successful/failed agents.

### Decision responsibilities
- Execution grouping derived from dependencies (parallel vs sequential).
- Retry/backoff policy for each agent invocation.
- Circuit breaker state and cache usage.
- Aggregation behavior when partial failures occur.
- Optional external research enrichment when prompt metadata indicates vendor/compliance needs.

### Must / must-not behaviors
- **Must** honor dependency ordering in routing entries.
- **Must** preserve correlation/tenant metadata when invoking downstream agents.
- **Must** emit audit events for invocations, failures, and aggregation.
- **Must** respect configured timeouts, retries, and concurrency limits.
- **Must not** re-route or reinterpret intents (owned by the Intent Router agent).
- **Must not** initiate approval workflows directly (owned by the Approval Workflow agent).
- **Must not** override downstream agent responses beyond aggregation and lightweight summarization.

## Overlap & handoff boundaries

### Intent Router
- **Overlap risk**: routing vs orchestration boundaries.
- **Boundary**: The Intent Router agent hands off the routing plan and parameters; the Response Orchestration agent executes exactly what is provided and returns results + summary. The Response Orchestration agent should not choose or reorder intents; if it receives empty or cyclic routing, it must return an error (cycle detection) rather than attempt to infer intent.

### Approval Workflow
- **Overlap risk**: the Response Orchestration agent should not implement approval logic itself.
- **Boundary**: The Approval Workflow agent owns approval gating and state transitions; the Response Orchestration agent only invokes the approval agent when included in routing. Ensure the routing plan includes the approval agent for guarded actions.

## Functional gaps / inconsistencies & alignment needs

- **Prompt metadata alignment**: ensure prompt templates and UI inputs supply `prompt_id`, `prompt_description`, and `prompt_tags` consistently so external research behavior is deterministic.
- **Routing contract**: `depends_on` should be validated upstream in the Intent Router agent and/or `config/agents/intent-routing.yaml` to avoid runtime dependency cycles.
- **Connector alignment**: downstream agents that require approval should expose explicit actions so the routing plan can include the Approval Workflow agent prior to execution.
- **UI/UX alignment**: surface partial-failure aggregation messaging to users so they understand which agents succeeded vs failed.

## Checkpoint: orchestration flow + dependency map entry

**Flow:** `the Intent Router agent (Intent Router) → the Response Orchestration agent (Response Orchestration) → Downstream Agents → Aggregated Response`

**Dependencies:**
- Upstream: the Intent Router agent provides `routing` entries and shared parameters.
- Downstream: specialized agents execute tasks; the Approval Workflow agent is invoked only if the routing plan includes approval-specific agents/actions.
- Shared services: event bus (publish `agent.requested`, `agent.completed`, `agent.failed`), audit logging, and observability metrics.

## What's inside

- [src](/agents/core-orchestration/response-orchestration-agent/src): Implementation source for this component.
- [tests](/agents/core-orchestration/response-orchestration-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/core-orchestration/response-orchestration-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name response-orchestration-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/core-orchestration/response-orchestration-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
