# Agent 14: Quality Management Specification

## Purpose

Define the responsibilities, workflows, and integration points for Agent 14: Quality Management. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

## What's inside

- `agents/delivery-management/agent-14-quality-management/src`: Implementation source for this component.
- `agents/delivery-management/agent-14-quality-management/tests`: Test suites and fixtures.
- `agents/delivery-management/agent-14-quality-management/Dockerfile`: Container build recipe for local or CI use.

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
