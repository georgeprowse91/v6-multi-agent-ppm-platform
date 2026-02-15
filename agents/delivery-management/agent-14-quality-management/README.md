# Agent 14: Quality Management Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 14: Quality Management. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- [src](/agents/delivery-management/agent-14-quality-management/src): Implementation source for this component.
- [tests](/agents/delivery-management/agent-14-quality-management/tests): Test suites and fixtures.
- [Dockerfile](/agents/delivery-management/agent-14-quality-management/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-14-quality-management --dry-run
```

Run unit tests (if present):

```bash
pytest agents/delivery-management/agent-14-quality-management/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. Check the agent implementation under `src/` for any additional required environment variables.

## Scope validation & decision boundaries

### Intended scope (Agent 14 owns)

Agent 14 owns **quality planning, test management, defect tracking, and quality analytics** across delivery workstreams. Its scope includes:

- Quality plan creation/approval, standards/acceptance criteria, and metric definitions.
- Test case/suite management, execution tracking, and coverage reporting.
- Defect logging, updates, trend analysis, root cause analysis, and quality reporting.
- Quality dashboards and release-readiness quality gate evaluation inputs.

### Inputs / outputs (validated behaviors)

The agent validates required inputs for specific actions and returns structured outputs that downstream agents can consume:

- **Inputs (required by action):**
  - `create_quality_plan`: `plan.project_id`, `plan.objectives`
  - `approve_quality_plan`: `plan_id`
  - `log_defect`: `defect.summary`, `defect.severity`, `defect.component`
  - `link_test_case_requirements`: `link.test_case_id`, `link.requirement_ids`
  - `update_test_case_links`: `link_id`
  - `sync_defect_tickets`: `defect_ids`
  - All actions accept `context.tenant_id` / `context.correlation_id` when provided.
- **Outputs (by action):**
  - Plans: plan ID + objectives + status + recommended metrics.
  - Tests: test case/suite IDs + execution results + coverage + artifacts.
  - Defects: defect ID + workflow status + trend analysis + RCA summaries.
  - Reporting: quality dashboards, quality reports, and gate readiness signals.

### Decision responsibilities (what Agent 14 decides)

- Approves or rejects quality plans **when the approval workflow agent is enabled** (status normalization and plan state transitions).
- Computes quality metrics and determines **quality gate readiness** based on defined thresholds.
- Determines defect trend classifications and RCA recommendations.

### Must / must-not behaviors

**Must:**
- Validate required inputs for each action before processing.
- Persist quality plans, test artifacts, defects, and audit findings.
- Publish quality events for downstream orchestration when plans/defects/tests are updated.
- Provide deterministic quality gate criteria and evaluation results for release decisions.

**Must not:**
- Make release deployment decisions (belongs to Agent 18).
- Own risk/issue register decisions or enterprise risk treatment plans (belongs to Agent 15).
- Override stakeholder release governance without documented quality gate outputs.

## Overlap/leakage analysis & handoff boundaries

### Agent 15 (Risk & Issue Management)

**Overlap risk:** Defect trends and RCA recommendations can look like “issue management.”  
**Boundary:** Agent 14 **tracks defects and quality-specific issues**; Agent 15 **owns enterprise risk/issue registers, mitigation plans, and escalation decisions**.  
**Handoff:** When defect trends indicate delivery risk (e.g., defect density threshold breach or repeated escape patterns), Agent 14 must emit a risk signal to Agent 15 with severity, trend, and recommended mitigation options.

### Agent 18 (Release Deployment)

**Overlap risk:** Quality gates are part of release readiness.  
**Boundary:** Agent 14 **defines and evaluates quality gates**, while Agent 18 **decides release sequencing, deployment approvals, and rollout mechanics**.  
**Handoff:** Agent 14 provides gate results (pass/fail + metrics + defects summary) to Agent 18 for final release decisioning and deployment orchestration.

## Functional gaps / inconsistencies & alignment needs

- **Prompt alignment:** Ensure prompts request “quality gate evidence” (coverage, defect density, pass rate, outstanding critical defects) instead of generic “go/no-go” language.
- **Tool alignment:** Map quality actions to existing integration mocks (Azure DevOps Test Plans, Jira Xray, TestRail, Playwright) and ensure identifiers are passed through to Agent 18 for release tickets.
- **Template alignment:** Standardize report templates so that quality gate outputs are formatted for Agent 18 consumption (gate status + thresholds + exceptions).
- **Connector alignment:** Confirm connectors can ingest/emit defect IDs and test run artifacts for cross-agent traceability.
- **UI alignment:** UI components should surface “Quality Gate Status,” “Coverage %,” “Defect Density,” and “Open Critical Defects” with drill-down to test and defect artifacts.

## Quality gate definitions (execution-ready)

Use the following default gate definitions unless overridden by config:

- **Coverage Gate:** `coverage_pct >= min_test_coverage` (default 80%).
- **Defect Density Gate:** `defect_density <= defect_density_threshold` (default 0.05 per KLOC).
- **Execution Pass Rate Gate:** `pass_rate_pct >= 95%` for the most recent execution window.
- **Regulated Audit Gate (conditional):** `audit_score >= 90%` when project type is compliance/regulated.

Gate results should be reported as `pass|fail`, include metric values, and provide any exceptions required for release governance.

### Quality management integrations

The quality management agent supports the following configuration keys (all optional) in its config payload:

```json
{
  "azure_devops": { "enabled": true, "organization": "<org>", "project": "<project>" },
  "jira_xray": { "enabled": true, "base_url": "<url>", "project_key": "<key>" },
  "testrail": { "enabled": true, "base_url": "<url>", "project_id": "<id>" },
  "playwright": { "browser": "chromium", "headless": true },
  "blob_storage": { "container": "quality-tests" },
  "azure_ml": { "workspace": "<name>", "model_name": "defect-predictor" },
  "code_repos": {
    "coverage_by_project": { "project-1": { "coverage_pct": 87.5, "source": "ado", "captured_at": "..." } },
    "size_by_project": { "project-1": { "kloc": 12.4, "source": "ado" } }
  },
  "azure_openai": { "prompt_prefix": "Use executive tone" }
}
```

These settings let the agent simulate (or integrate with) Azure DevOps Test Plans, Jira Xray, TestRail, Playwright automation runs, Blob Storage artifacts, Azure ML defect prediction, and coverage metrics collected from code repositories. Release notes and quality reports are generated with Azure OpenAI prompt templates using the provided `prompt_prefix` when available.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
