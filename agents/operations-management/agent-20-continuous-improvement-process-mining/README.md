# Agent 20: Continuous Improvement Process Mining Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 20: Continuous Improvement Process Mining. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Intended scope

Agent 20 owns continuous improvement and process mining for operational workflows. It ingests
execution event logs, discovers as-is process models, checks conformance against designed
processes, detects bottlenecks/deviations, and turns findings into improvement initiatives with
benefit tracking. It is not a general analytics warehouse or workflow engine; it is the
process-insight-to-improvement loop.

### Primary responsibilities

- Ingest and validate event logs for process instances.
- Discover process models and performance metrics from execution traces.
- Detect bottlenecks, deviations, and root causes.
- Generate improvement recommendations and backlog items.
- Track benefit realization and benchmark performance.
- Share best practices with the knowledge agent and notify workflow engine of improvement
  recommendations.

## Inputs and outputs

### Inputs

- `events` payloads for `ingest_event_log` (event logs with case/process identifiers).
- `process_id` and optional `algorithm` for process discovery.
- `process_id` plus `expected_model` or `process_model_id` for conformance.
- `issue_id` for root cause analysis.
- `improvement` payload for creating improvement initiatives.
- `benchmark_criteria` or filters for benchmarking and reporting.
- Optional `tenant_id` for multi-tenant storage scoping.
- `analytics_report` payload for `ingest_analytics_report` containing periodic trends, anomalies, and recommendations from Agent 22.

### Outputs

- Process models (activities, transitions, BPMN/Petri net representations).
- Conformance reports with compliance rates and deviations.
- Bottleneck and deviation analyses with recommendations.
- Improvement backlog entries with priority scores and expected benefits.
- Benefit realization metrics and ROI summaries.
- KPI rollups for process/project/program levels.
- Analytics-driven improvement backlog items with owners and target dates.
- Persisted improvement completion history (`date`, `owner`, `outcome`) retrievable by tenant.

## Decision responsibilities

Agent 20 is responsible for:

- Selecting mining algorithms for discovery (defaulting to heuristic miner).
- Determining bottleneck thresholds and deviation thresholds for alerts.
- Prioritizing improvements based on benefits and feasibility scoring.
- Emitting workflow improvement recommendations to the workflow engine.

Agent 20 is not responsible for:

- Approving or executing workflow changes (Agent 24 handles workflow execution).
- Curating enterprise-wide analytics models/warehouses (Agents 22/25).
- Authoring enterprise policy or compliance rules (handled by governance agents).

## Must / must-not behaviors

### Must

- Validate action inputs before processing.
- Persist event logs, models, conformance reports, and recommendations by tenant.
- Emit improvement recommendation events to the workflow engine when improvements are created.
- Publish process discovery and benefit realization events to the event bus.

### Must not

- Trigger workflow execution directly outside of the workflow engine interface.
- Overwrite curated analytics KPIs owned by analytics agents.
- Generate recommendations without traceable evidence from event logs/metrics.

## Overlap and handoff boundaries

### Analytics agent (Agent 22)

- **Overlap**: Both Agent 20 and Agent 22 compute KPIs and performance metrics.
- **Boundary**: Agent 20 computes process-level KPIs for improvement decisions; Agent 22
  consolidate portfolio-wide KPIs, predictive analytics, and dashboarding.
- **Handoff**: Agent 20 publishes process insights and benefit realization events; analytics
  agent consumes these events for enterprise reporting and forecasting.

### Workflow engine (Agent 24)

- **Overlap**: Both agents operate on process models.
- **Boundary**: Agent 20 discovers as-is models and recommends improvements; Agent 24 owns the
  execution of to-be workflows and orchestration definitions.
- **Handoff**: Agent 20 emits `workflow.improvement.recommendation` events to Agent 24; Agent 24
  updates workflows, approvals, and execution state.

## Functional gaps and required alignment

### Gaps / inconsistencies

- Improvement backlog persistence is currently in-memory while other artifacts are tenant-stored.
- Deviation and bottleneck thresholds are static defaults; no configuration guardrails are
  documented for tenant overrides.
- KPI rollups overlap analytics agent scopes without explicit governance rules.

### Required alignment (prompt/tool/template/connector/UI)

- **Prompt**: Ensure agent prompt explicitly distinguishes process-improvement KPIs vs enterprise
  analytics KPIs to avoid overlap with Agents 22/25.
- **Tooling**: Align event schemas with analytics ingestion (`events.ingested`,
  `process.discovered`, `benefits.realized`) to avoid schema drift.
- **Templates**: Provide a standard improvement initiative template shared with Agent 24 to
  translate recommendations into workflow updates.
- **Connectors**: Ensure task-sync integration is configured for improvement backlog handoff.
- **UI**: Expose improvement backlog, conformance reports, and benefit tracking dashboards
  separate from global analytics dashboards.

## Improvement feedback loop (checkpoint)

1. **Ingest**: Receive execution events via `ingest_event_log` and persist by tenant.
2. **Discover**: Build as-is process models and performance metrics.
3. **Assess**: Run conformance, bottleneck, and deviation analyses.
4. **Diagnose**: Perform root cause analysis for prioritized issues.
5. **Recommend**: Generate improvement initiatives with expected benefits and priority scoring.
6. **Handoff**: Emit `workflow.improvement.recommendation` events to Agent 24 and create tasks.
7. **Implement**: Workflow engine executes approved changes (Agent 24 responsibility).
8. **Track**: Measure realized benefits, update KPIs, and publish benefit events.
9. **Benchmark**: Compare against internal/external benchmarks for continuous calibration.

## Closed-loop analytics integration (Agent 22 → Agent 20)

Agent 20 now consumes analytics insights to operationalize continuous improvement:

1. Receive periodic analytics via `ingest_analytics_report`.
2. Convert recommendations into backlog items, categorize them, and prioritize by impact/feasibility.
3. Assign default or rule-based owners and set target dates.
4. Publish the generated backlog to knowledge management (`knowledge_agent`) or event topic fallback (`knowledge.improvement_backlog.published`).
5. Notify stakeholders on additions/completions through notification integration (`notification_service`) or event fallback (`notification.improvement`).
6. Mark actions complete with `complete_improvement`.
7. Persist completed actions into `improvement_history_store` and retrieve with `get_improvement_history`.

### Suggested payload contract for `ingest_analytics_report`

```json
{
  "action": "ingest_analytics_report",
  "tenant_id": "tenant-a",
  "analytics_report": {
    "report_id": "RPT-2026-01",
    "period": "monthly",
    "recommendations": ["..."],
    "anomalies": [{"metric": "cycle_time_days", "value": 25}],
    "trends": [{"pattern": "recurring_scope_creep", "count": 4}]
  }
}
```

## What's inside

- [src](/agents/operations-management/agent-20-continuous-improvement-process-mining/src): Implementation source for this component.
- [tests](/agents/operations-management/agent-20-continuous-improvement-process-mining/tests): Test suites and fixtures.
- [Dockerfile](/agents/operations-management/agent-20-continuous-improvement-process-mining/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-20-continuous-improvement-process-mining --dry-run
```

Run unit tests (if present):

```bash
pytest agents/operations-management/agent-20-continuous-improvement-process-mining/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
