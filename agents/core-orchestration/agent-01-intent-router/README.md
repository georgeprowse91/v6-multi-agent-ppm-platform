# Agent 01: Intent Router Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 01: Intent Router. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Scope and decision responsibilities

**Scope (in-scope responsibilities)**
- Classify user queries into one or more intents using an LLM-backed classifier with a deterministic fallback.
- Normalize intent confidence and enforce minimum confidence thresholds per intent before routing.
- Map validated intents to downstream agent routes defined in the routing configuration.
- Extract basic parameters from the query to pass downstream (project/portfolio IDs, currency, amount, schedule focus).
- Emit audit events for classifications and fallback usage.

**Out of scope (must-not behaviors)**
- Do **not** generate the final user response; downstream domain agents and Agent 02 handle response assembly.
- Do **not** execute domain logic or approvals; Agent 03 (approval workflow) and domain agents own those flows.
- Do **not** route intents that are not present in the routing configuration or below confidence thresholds.

## Inputs and outputs

**Inputs**
- Required: `query` (non-empty string).
- Optional: `context` (dictionary) including `tenant_id` and `correlation_id`.

**Outputs**
- `intents`: normalized list of intents with confidence scores.
- `routing`: list of target agents, each containing `agent_id`, `intent`, `priority`, optional `action`, and `depends_on`.
- `parameters`: extracted parameters for downstream agents.
- Echoed `query` and `context` for traceability.

## Handoff boundaries with Agent 02 and Agent 03

- **Agent 02 (Response Orchestration)**: consumes `routing`, `intents`, and `parameters` from Agent 01 to orchestrate calls to downstream agents and merge their outputs. Agent 01 must not format final responses or merge downstream outputs.
- **Agent 03 (Approval Workflow)**: triggered only when routing rules or downstream agents indicate a governance requirement. Agent 01 should only route to Agent 03 when the configured intent routes include approval dependencies; Agent 03 owns escalation, policy checks, and approval state transitions.

## Functional gaps / inconsistencies to resolve

- **Prompt configuration coupling**: intent recognition depends on `agents/runtime/prompts/examples/intent-router.prompt.yaml`. Update both the routing config and prompt examples when adding new intents to avoid mismatches.
- **Routing config drift**: routing is driven by `config/agents/intent-routing.yaml`. If this config omits an intent returned by the LLM, Agent 01 will drop it; ensure config and prompts stay aligned.
- **Fallback behavior**: when LLM output is invalid/low-confidence, the fallback classifier only uses static keyword signals; expand or tune signals to avoid under-classification for new intents.
- **Parameter schema limits**: extracted parameters are currently minimal (project/portfolio IDs, currency, amount, schedule focus). Downstream agents requiring richer inputs must extend extraction logic or supply their own enrichment.

## Required prompt/tool/template/connector/UI alignment

- **Prompt**: `agents/runtime/prompts/examples/intent-router.prompt.yaml` must enumerate the same intent names defined in `config/agents/intent-routing.yaml`.
- **Routing config**: `config/agents/intent-routing.yaml` must include routes for any intent the prompt can emit; otherwise Agent 01 will not dispatch to downstream agents.
- **Audit/observability**: classification and fallback audit events must be consumed by observability tooling to support traceability.

## Checkpoint: scope + dependency map entry

- **Dependencies**: LLM client, prompt registry, audit event pipeline, intent routing configuration.
- **Execution flow**: validate input → prompt LLM → normalize intents → apply config thresholds → extract parameters → map to routes → emit audit events → return routing payload.

## What's inside

- [agents/core-orchestration/agent-01-intent-router/src](/agents/core-orchestration/agent-01-intent-router/src): Implementation source for this component.
- [agents/core-orchestration/agent-01-intent-router/tests](/agents/core-orchestration/agent-01-intent-router/tests): Test suites and fixtures.
- [agents/core-orchestration/agent-01-intent-router/Dockerfile](/agents/core-orchestration/agent-01-intent-router/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-01-intent-router --dry-run
```

Run unit tests (if present):

```bash
pytest agents/core-orchestration/agent-01-intent-router/tests
```

## Advanced classification and extraction

- Transformer-based classifier support is enabled via `transformers` using `distilbert-base-uncased` (or local fine-tuned artifacts under `models/intent_classifier/`).
- Multi-intent output returns the top-2 intents with confidence scores, filtered by global and per-intent thresholds.
- Entity extraction uses spaCy (with an entity ruler fallback) to capture `portfolio_id`, `project_id`, `currency`, `amount`, and `schedule_focus`.
- Extracted parameters are validated against the `ExtractedParameters` schema before returning to downstream agents.

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

### Routing configuration

Intent routing is defined in `config/agents/intent-routing.yaml`. The file declares each intent, minimum confidence thresholds, and the agent/action routes to invoke. Validate updates with:

```bash
python scripts/validate-intent-routing.py
```

### Adding a new intent (no code changes)

1. Add a new intent entry in `config/agents/intent-routing.yaml` with `name`, `min_confidence`, and at least one `routes` entry containing the target `agent_id` and optional `action`/`dependencies`.
2. Update the intent routing prompt if you need the LLM to recognize the new intent (`agents/runtime/prompts/examples/intent-router.prompt.yaml`).
3. Run `python scripts/validate-intent-routing.py` and update tests if you changed intent behavior.

### Migration notes

- The intent → agent/action mapping previously lived in `IntentRouterAgent._determine_agents`.
- Mapping updates now live in `config/agents/intent-routing.yaml`, so routing changes no longer require code changes.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
