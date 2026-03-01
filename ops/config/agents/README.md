# Agent Configuration

## Overview

This directory contains agent runtime, orchestration, and intent routing configuration for the multi-agent PPM platform. Configuration files define domain agent behavior, the intent router, and response orchestration settings.

## Directory structure

| Path | Description |
| --- | --- |
| [schema/](./schema/) | JSON schema for intent routing configuration validation |
| [agent-23/](./agent-23/) | Per-agent config for Agent 23 – Data Synchronization & Quality |
| [agent-24/](./agent-24/) | Per-agent config for Agent 24 – Workflow & Process Engine |

## Key files

| File | Applies to | Description |
| --- | --- | --- |
| [intent-routing.yaml](./intent-routing.yaml) | Agent 01 – Intent Router | Intent definitions and routing targets. Canonical design reference; see note below on runtime vs design config. |
| [intent-router.yaml](./intent-router.yaml) | Agent 01 – Intent Router | LLM model, extraction, and fallback settings for the intent router. |
| [orchestration.yaml](./orchestration.yaml) | Agent 01 + 02 | Intent router and response orchestration agent settings. |
| [portfolio.yaml](./portfolio.yaml) | Agents 04–07 | Domain agent behavior for demand intake, business case, portfolio strategy, and program management. |
| [knowledge_agent.yaml](./knowledge_agent.yaml) | Agent 19 | Semantic search, embeddings, and summarization settings for knowledge/document management. |
| [approval_policies.yaml](./approval_policies.yaml) | Agent 03 | Approval workflow escalation and threshold policy including risk/criticality-driven timeouts. |
| [approval_workflow.yaml](./approval_workflow.yaml) | Agent 03 | Approval workflow runtime toggles including delegation enablement and default delegation duration. |
| [business-case-settings.yaml](./business-case-settings.yaml) | Agent 05 | Business case scoring weights, ROI thresholds, and template settings. |
| [risk_adjustments.yaml](./risk_adjustments.yaml) | Agent 15 | Risk scoring adjustment factors and severity thresholds. |
| [demo-participants.yaml](./demo-participants.yaml) | All (demo mode) | Demo participant configuration for local and demo environments. |

### Per-agent config directories

Complex agents with many config files use a dedicated subdirectory:

| Directory | Agent | Files |
| --- | --- | --- |
| [agent-23/](./agent-23/) | Agent 23 – Data Sync | `mapping_rules.yaml`, `quality_thresholds.yaml`, `pipelines.yaml`, `schema_registry.yaml`, `validation_rules.yaml` |
| [agent-24/](./agent-24/) | Agent 24 – Workflow Engine | `durable_workflows.yaml`, `workflow_templates.yaml` |

## Notes

**Intent routing — design vs runtime config:**
`intent-routing.yaml` in this directory is the canonical design reference. Agents 13–25 are intended to have descriptive IDs (e.g. `risk-management`). The live runtime config at `services/agent-runtime/src/config/intent-routing.yaml` currently uses numeric IDs (e.g. `agent_015`) because that is how those agents are registered in `runtime.py`. Both files should be kept in sync for intent names and non-ID fields.

**Validation:**

```bash
python -m jsonschema -i ops/config/agents/intent-routing.yaml ops/config/agents/schema/intent-routing.schema.json
```

**Environment variable overrides:**

Most config values can be overridden via environment variables at runtime. Key overrides:

| Env var | Overrides | Default |
| --- | --- | --- |
| `INTENT_ROUTING_CONFIG_PATH` | Agent 01 routing config path | `ops/config/agents/intent-routing.yaml` |
| `DURABLE_WORKFLOW_CONFIG` | Agent 24 durable workflows path | `ops/config/agents/agent-24/durable_workflows.yaml` |
| `WORKFLOW_TEMPLATES_PATH` | Agent 24 workflow templates path | `ops/config/agents/agent-24/workflow_templates.yaml` |
