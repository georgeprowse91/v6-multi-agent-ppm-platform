# Agent 17: Change Configuration Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 17: Change Configuration. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- `agents/operations-management/agent-17-change-configuration/src`: Implementation source for this component.
- `agents/operations-management/agent-17-change-configuration/tests`: Test suites and fixtures.
- `agents/operations-management/agent-17-change-configuration/Dockerfile`: Container build recipe for local or CI use.

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
  "impact_model_samples": [
    {"complexity": 2.0, "historical_failure_rate": 0.1, "affected_services": 3, "risk_category": "medium", "success_probability": 0.85}
  ],
  "event_bus": {"topic_name": "ppm-events"}
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
    "knowledge_query": "AKS scaling runbook"
  }
}
```

## Troubleshooting

- `run-agent` fails with missing entrypoint: ensure a Python module exists under `src/`.
- Runtime errors about missing secrets: populate the required env vars in `.env`.
- Docker execution fails: verify Docker is running and the agent has a `Dockerfile`.
