# Intent Router Agent Specification

## Purpose

Define the responsibilities, workflows, and integration points for the Intent Router Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Intended scope

### Responsibilities
- Classify user queries into one or more intents using an LLM-backed classifier with a deterministic fallback.
- Normalize intent confidence and enforce minimum confidence thresholds per intent before routing.
- Map validated intents to downstream agent routes defined in the routing configuration.
- Extract basic parameters from the query to pass downstream (project/portfolio IDs, currency, amount, schedule focus).
- Emit audit events for classifications and fallback usage.

### Inputs
- Required: `query` (non-empty string).
- Optional: `context` (dictionary) including `tenant_id` and `correlation_id`.

### Outputs
- `intents`: normalized list of intents with confidence scores.
- `routing`: list of target agents, each containing `agent_id`, `intent`, `priority`, optional `action`, and `depends_on`.
- `parameters`: extracted parameters for downstream agents.
- Echoed `query` and `context` for traceability.

### Decision responsibilities
- Select the best-matching intent(s) from LLM output and apply confidence thresholds.
- Determine which downstream agents to route to based on intent-routing configuration.
- Fall back to deterministic keyword classifier when LLM output is invalid or low-confidence.

### Must / must-not behaviors
- **Must** validate that `query` is non-empty before processing.
- **Must** normalize intent confidence and apply per-intent thresholds from routing config.
- **Must** emit audit events for every classification and fallback usage.
- **Must not** generate the final user response; downstream domain agents and the Response Orchestration agent handle response assembly.
- **Must not** execute domain logic or approvals; the Approval Workflow agent and domain agents own those flows.
- **Must not** route intents that are not present in the routing configuration or below confidence thresholds.

## Overlap & handoff boundaries

### Response Orchestration
- **Overlap risk**: both agents participate in the routing-to-execution pipeline.
- **Boundary**: The Response Orchestration agent consumes `routing`, `intents`, and `parameters` from the Intent Router agent to orchestrate calls to downstream agents and merge their outputs. The Intent Router agent must not format final responses or merge downstream outputs.

### Approval Workflow
- **Overlap risk**: intent routing may trigger approval-dependent flows.
- **Boundary**: The Intent Router agent should only route to the Approval Workflow agent when the configured intent routes include approval dependencies; the Approval Workflow agent owns escalation, policy checks, and approval state transitions.

## Functional gaps / inconsistencies & alignment needs

- **Prompt configuration coupling**: intent recognition depends on `agents/runtime/prompts/examples/intent-router.prompt.yaml`. Update both the routing config and prompt examples when adding new intents to avoid mismatches.
- **Routing config drift**: routing is driven by `config/agents/intent-routing.yaml`. If this config omits an intent returned by the LLM, the Intent Router agent will drop it; ensure config and prompts stay aligned.
- **Fallback behavior**: when LLM output is invalid/low-confidence, the fallback classifier only uses static keyword signals; expand or tune signals to avoid under-classification for new intents.
- **Parameter schema limits**: extracted parameters are currently minimal (project/portfolio IDs, currency, amount, schedule focus). Downstream agents requiring richer inputs must extend extraction logic or supply their own enrichment.
- **Prompt alignment**: `agents/runtime/prompts/examples/intent-router.prompt.yaml` must enumerate the same intent names defined in `config/agents/intent-routing.yaml`.
- **Routing config alignment**: `config/agents/intent-routing.yaml` must include routes for any intent the prompt can emit; otherwise the Intent Router agent will not dispatch to downstream agents.
- **Audit/observability**: classification and fallback audit events must be consumed by observability tooling to support traceability.

## Checkpoint: scope + dependency map entry

- **Dependencies**: LLM client, prompt registry, audit event pipeline, intent routing configuration.
- **Execution flow**: validate input → prompt LLM → normalize intents → apply config thresholds → extract parameters → map to routes → emit audit events → return routing payload.

## What's inside

- [src](/agents/core-orchestration/intent-router-agent/src): Implementation source for this component.
- [tests](/agents/core-orchestration/intent-router-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/core-orchestration/intent-router-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name intent-router-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/core-orchestration/intent-router-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

### Advanced classification and extraction

- Transformer-based classifier support is enabled via `transformers` using `distilbert-base-uncased` (or local fine-tuned artifacts under `models/intent_classifier/`).
- Multi-intent output returns the top-2 intents with confidence scores, filtered by global and per-intent thresholds.
- Entity extraction uses spaCy (with an entity ruler fallback) to capture `portfolio_id`, `project_id`, `currency`, `amount`, and `schedule_focus`.
- Extracted parameters are validated against the `ExtractedParameters` schema before returning to downstream agents.

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
