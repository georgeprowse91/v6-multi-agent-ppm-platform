# Agent 17: Change Configuration Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 17: Change Configuration. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- [src](/agents/operations-management/agent-17-change-configuration/src): Implementation source for this component.
- [tests](/agents/operations-management/agent-17-change-configuration/tests): Test suites and fixtures.
- [Dockerfile](/agents/operations-management/agent-17-change-configuration/Dockerfile): Container build recipe for local or CI use.

## How it's used

Referenced by the agent runtime and orchestration docs when routing requests, and discovered by `tools/agent_runner` during local execution.

## How to run / develop / test

Run the agent locally with the shared runner:

```bash
python -m tools.agent_runner run-agent --name agent-17-change-configuration --dry-run
```

Run unit tests (if present):

```bash
pytest agents/operations-management/agent-17-change-configuration/tests
```

## Configuration

Agent runtime configuration is centralized in `.env` (see `.env.example`) and shared agent settings such as `MAX_AGENT_CONCURRENCY` and `AGENT_TIMEOUT_SECONDS`. The change agent also uses the environment variables below for integrations.

### Integration environment variables

| Variable | Purpose |
| --- | --- |
| `GITHUB_TOKEN` | GitHub REST API access for repo metadata, PR status, and commit diffs. |
| `GITLAB_TOKEN` | GitLab REST API access for repo metadata, merge requests, and commit diffs. |
| `AZURE_DEVOPS_TOKEN` | Azure Repos/DevOps REST API access for repos and PR status. |
| `SERVICE_BUS_CONNECTION_STRING` | Azure Service Bus connection for change events. |
| `COSMOS_DB_CONNECTION_STRING` | Persist workflow state in Cosmos DB. |
| `DURABLE_FUNCTIONS_URL` | Azure Durable Functions orchestration endpoint. |
| `LOGIC_APPS_URL` | Azure Logic Apps orchestration endpoint. |
| `SHAREPOINT_SITE_URL` | Enable SharePoint connector for change context documents. |
| `CONFLUENCE_BASE_URL` | Enable Confluence connector (if configured) for KB articles. |
| `NEO4J_URI` | Neo4j graph database URI for CI dependency storage. |
| `NEO4J_USERNAME` | Neo4j username. |
| `NEO4J_PASSWORD` | Neo4j password. |

### Agent configuration highlights

Use the agent config to point at workflow orchestration and modeling options:

```json
{
  "workflow_orchestrator": "durable_functions",
  "workflow_config": {
    "durable_functions_url": "https://example.azurewebsites.net/api/orchestrate"
  },
  "impact_model_samples": [
    {"complexity": 2.0, "historical_failure_rate": 0.1, "affected_services": 3, "risk_category": "medium", "success_probability": 0.85}
  ],
  "event_bus": {"topic_name": "ppm-events"},
  "cicd_subscriptions": [
    {"tool": "azure_devops", "endpoint": "https://hooks.example.com/change", "events": ["deployment"]}
  ]
}
```

## Change workflow example

1. **Submit change request** with repository references and IaC file paths.
2. **Agent enriches context** with repo metadata, IaC resource diff parsing, and KB articles.
3. **Approval workflow** creates tasks for peer review, automated checks, and final approval.
4. **CI/CD updates** arrive via webhook payloads to update deployment status.
5. **Events published** to Service Bus topics (`change.created`, `change.approved`, `change.rolled_back`).

Example payload:

```json
{
  "action": "submit_change_request",
  "change": {
    "title": "Scale AKS cluster",
    "description": "Increase node pool size for workload growth",
    "requester": "platform",
    "repo_provider": "github",
    "repo_slug": "org/platform-infra",
    "pull_request_id": "42",
    "iac_files": ["infra/terraform/aks.tf"],
    "iac_repo_path": "infra",
    "knowledge_query": "AKS scaling runbook"
  }
}
```

## Scope validation

### Intended scope (what Agent 17 owns)

- Change request intake, classification, and risk/impact assessment.
- Approval workflow coordination and auditing.
- CMDB/CI registration, baselines, and dependency visualization.
- Change implementation gating (staging/automated tests) and rollback triggers.
- Publishing change events/metrics to the event bus and notifying stakeholders.

### Inputs (expected)

- `action` (required): One of the supported actions in `process` (e.g., `submit_change_request`, `assess_impact`, `approve_change`, `implement_change`, `cicd_webhook`).
- `change` (for submit/predict): Title, description, requester, priority, repo references (`repo_provider`, `repo_slug`, `pull_request_id`, `commit_id`), IaC paths (`iac_files`, `iac_repo_path`), optional `ci_ids`, `risk_category`, `knowledge_query`.
- `approval`, `review`, `implementation`, `updates`, and `filters` payloads for respective actions.
- `context` (optional): `tenant_id`, `correlation_id`, `user_id` (actor) for traceability.

### Outputs (guaranteed)

- Structured JSON payloads that include `change_id` and status fields for each action.
- Persisted change records, audit entries, and CMDB updates via storage services.
- Published events for lifecycle steps (created, approved/rejected, implementation started, rolled back, metrics).

### Decision responsibilities

- **Must decide**: change classification, approval routing, approval requirement, risk/impact recommendations, and whether to proceed/roll back based on staging/tests.
- **Must not decide**: final deployment scheduling mechanics (delegated to Agent 18), workflow orchestration definition/templating (delegated to Agent 24), or approval policy governance beyond configured thresholds.

### Must / must-not behaviors

**Must**
- Validate `action` and required fields for `submit_change_request`.
- Persist change records and audit entries on each state transition.
- Enrich change context with repo/IaC/knowledge data when provided.
- Publish events for key lifecycle transitions.

**Must not**
- Deploy releases directly or manage runtime deployment plans.
- Modify workflow templates or orchestration definitions owned by the workflow engine.
- Bypass approval requirements when thresholds dictate approval.

## Overlap analysis and handoff boundaries

### Agent 18: Release Deployment

**Potential overlap**
- Change implementation and deployment coordination are adjacent to release orchestration.

**Handoff boundary**
- Agent 17 **initiates** deployment coordination via `release_deployment_endpoint` and only tracks deployment status updates (e.g., `cicd_webhook`).
- Agent 18 **executes** release/deployment orchestration, scheduling, and rollout mechanics, then reports status back.

### Agent 24: Workflow Process Engine

**Potential overlap**
- Both handle workflow orchestration; Agent 17 builds a change workflow instance.

**Handoff boundary**
- Agent 17 **requests** workflow creation and manages change state; Agent 24 **owns** workflow definitions, step orchestration, retries/compensation, and workflow persistence.

## Gaps, inconsistencies, and alignment requirements

- **Workflow orchestration alignment**: Agent 17 uses `workflow_orchestrator` config (Durable Functions or Logic Apps), while Agent 24 defines workflow specs/templates. Align on a shared workflow schema and ensure Agent 17 payloads conform to the templates/versions maintained by Agent 24.
- **Deployment status contract**: Agent 17 expects `deployment_status` values (`scheduled`, `succeeded`, `failed`). Formalize a shared status enum with Agent 18, including intermediate states (queued, in-progress, rolled-back).
- **Approval policy governance**: Agent 17 uses `approval_priority_thresholds` and `approval_change_types`. Document org-wide policy ownership and how updates propagate to avoid bypassing CAB requirements.
- **Event taxonomy**: Agent 17 emits `change.*` and `stakeholder.comms.*` events. Verify event names/fields match the platform-wide event schema used by Agents 18 and 24.
- **Connector/UI alignment**: Ensure UI fields for change intake map to the expected input keys (`repo_provider`, `repo_slug`, IaC paths) and that connectors (ITSM, repo APIs, Service Bus) are configured consistently across environments.

### Checkpoint: change control handoffs

- Agent 17 submits change workflows (creates/updates change state).
- Agent 24 runs and governs workflow definitions/execution.
- Agent 18 executes deployment and reports status.

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
