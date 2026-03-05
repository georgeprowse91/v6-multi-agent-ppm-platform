# Continuous Improvement Agent Specification

## Purpose

Define the responsibilities, workflows, and integration points for the Continuous Improvement Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## Intended scope

### Responsibilities
- Ingest and validate event logs for process instances.
- Discover process models and performance metrics from execution traces.
- Detect bottlenecks, deviations, and root causes.
- Generate improvement recommendations and backlog items.
- Track benefit realization and benchmark performance.
- Share best practices with the Knowledge Management agent and notify the Approval Workflow agent of improvement recommendations.
- Consume periodic analytics from the Analytics Insights agent to operationalize continuous improvement.

### Inputs
- `events` payloads for `ingest_event_log` (event logs with case/process identifiers).
- `process_id` and optional `algorithm` for process discovery.
- `process_id` plus `expected_model` or `process_model_id` for conformance.
- `issue_id` for root cause analysis.
- `improvement` payload for creating improvement initiatives.
- `benchmark_criteria` or filters for benchmarking and reporting.
- Optional `tenant_id` for multi-tenant storage scoping.
- `analytics_report` payload for `ingest_analytics_report` containing periodic trends, anomalies, and recommendations from the Analytics Insights agent.

### Outputs
- Process models (activities, transitions, BPMN/Petri net representations).
- Conformance reports with compliance rates and deviations.
- Bottleneck and deviation analyses with recommendations.
- Improvement backlog entries with priority scores and expected benefits.
- Benefit realization metrics and ROI summaries.
- KPI rollups for process/project/program levels.
- Analytics-driven improvement backlog items with owners and target dates.
- Persisted improvement completion history (`date`, `owner`, `outcome`) retrievable by tenant.

### Decision responsibilities
- Selecting mining algorithms for discovery (defaulting to heuristic miner).
- Determining bottleneck thresholds and deviation thresholds for alerts.
- Prioritizing improvements based on benefits and feasibility scoring.
- Emitting workflow improvement recommendations to the Approval Workflow agent.

### Must / must-not behaviors
- **Must** validate action inputs before processing.
- **Must** persist event logs, models, conformance reports, and recommendations by tenant.
- **Must** emit improvement recommendation events to the Approval Workflow agent when improvements are created.
- **Must** publish process discovery and benefit realization events to the event bus.
- **Must not** trigger workflow execution directly outside of the Approval Workflow agent.
- **Must not** overwrite curated analytics KPIs owned by analytics agents.
- **Must not** generate recommendations without traceable evidence from event logs/metrics.

## Overlap & handoff boundaries

### Analytics Insights
- **Overlap risk**: both the Continuous Improvement agent and the Analytics Insights agent compute KPIs and performance metrics.
- **Boundary**: The Continuous Improvement agent computes process-level KPIs for improvement decisions; the Analytics Insights agent consolidates portfolio-wide KPIs, predictive analytics, and dashboarding. The Continuous Improvement agent publishes process insights and benefit realization events; the Analytics Insights agent consumes these events for enterprise reporting and forecasting.

### Approval Workflow
- **Overlap risk**: both agents operate on process models.
- **Boundary**: The Continuous Improvement agent discovers as-is models and recommends improvements; the Approval Workflow agent owns the execution of to-be workflows and orchestration definitions. The Continuous Improvement agent emits `workflow.improvement.recommendation` events to the Approval Workflow agent; the Approval Workflow agent updates workflows, approvals, and execution state.

## Functional gaps / inconsistencies & alignment needs

- Improvement backlog persistence is currently in-memory while other artifacts are tenant-stored.
- Deviation and bottleneck thresholds are static defaults; no configuration guardrails are documented for tenant overrides.
- KPI rollups overlap analytics agent scopes without explicit governance rules.
- **Prompt alignment**: ensure agent prompt explicitly distinguishes process-improvement KPIs vs enterprise analytics KPIs to avoid overlap with analytics agents.
- **Tooling alignment**: align event schemas with analytics ingestion (`events.ingested`, `process.discovered`, `benefits.realized`) to avoid schema drift.
- **Template alignment**: provide a standard improvement initiative template shared with the Approval Workflow agent to translate recommendations into workflow updates.
- **Connector alignment**: ensure task-sync integration is configured for improvement backlog handoff.
- **UI alignment**: expose improvement backlog, conformance reports, and benefit tracking dashboards separate from global analytics dashboards.

## Checkpoint: improvement feedback loop

1. **Ingest**: Receive execution events via `ingest_event_log` and persist by tenant.
2. **Discover**: Build as-is process models and performance metrics.
3. **Assess**: Run conformance, bottleneck, and deviation analyses.
4. **Diagnose**: Perform root cause analysis for prioritized issues.
5. **Recommend**: Generate improvement initiatives with expected benefits and priority scoring.
6. **Handoff**: Emit `workflow.improvement.recommendation` events to the Approval Workflow agent and create tasks.
7. **Implement**: The Approval Workflow agent executes approved changes.
8. **Track**: Measure realized benefits, update KPIs, and publish benefit events.
9. **Benchmark**: Compare against internal/external benchmarks for continuous calibration.

## What's inside

- [src](/agents/operations-management/continuous-improvement-agent/src): Implementation source for this component.
- [tests](/agents/operations-management/continuous-improvement-agent/tests): Test suites and fixtures.
- [Dockerfile](/agents/operations-management/continuous-improvement-agent/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name continuous-improvement-agent --dry-run
```

Run unit tests (if present):

```bash
pytest agents/operations-management/continuous-improvement-agent/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `ops/config/.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

### Closed-loop analytics integration (Analytics Insights → Continuous Improvement)

The Continuous Improvement agent consumes analytics insights to operationalize continuous improvement:

1. Receive periodic analytics via `ingest_analytics_report`.
2. Convert recommendations into backlog items, categorize them, and prioritize by impact/feasibility.
3. Assign default or rule-based owners and set target dates.
4. Publish the generated backlog to knowledge management (`knowledge_agent`) or event topic fallback (`knowledge.improvement_backlog.published`).
5. Notify stakeholders on additions/completions through notification integration (`notification_service`) or event fallback (`notification.improvement`).
6. Mark actions complete with `complete_improvement`.
7. Persist completed actions into `improvement_history_store` and retrieve with `get_improvement_history`.

#### Suggested payload contract for `ingest_analytics_report`

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

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
