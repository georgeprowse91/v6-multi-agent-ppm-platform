# Agent Configuration

## Overview

This directory contains agent runtime, orchestration, and intent routing configuration for the multi-agent PPM platform. Configuration files define domain agent behavior, the intent router, and response orchestration settings.

## Directory structure

| Path | Description |
| --- | --- |
| [schema/](./schema/) | JSON schema for intent routing configuration validation |
| [data-synchronisation-agent/](./data-synchronisation-agent/) | Per-agent config for the Data Synchronisation agent – Data Synchronization & Quality |
| [approval-workflow-agent/](./approval-workflow-agent/) | Approval Workflow agent workflow configuration (durable workflow definitions and templates). |

## Key files

| File | Applies to | Description |
| --- | --- | --- |
| [intent-routing.yaml](./intent-routing.yaml) | the Intent Router agent – Intent Router | Intent definitions and routing targets. Canonical design reference; see note below on runtime vs design config. |
| [intent-router.yaml](./intent-router.yaml) | the Intent Router agent – Intent Router | LLM model, extraction, and fallback settings for the intent router. |
| [orchestration.yaml](./orchestration.yaml) | the Intent Router agent + 02 | Intent router and response orchestration agent settings. |
| [portfolio.yaml](./portfolio.yaml) | Agents 04–07 | Domain agent behavior for demand intake, business case, portfolio strategy, and program management. |
| [knowledge_agent.yaml](./knowledge_agent.yaml) | the Knowledge Management agent | Semantic search, embeddings, and summarization settings for knowledge/document management. |
| [approval_policies.yaml](./approval_policies.yaml) | the Approval Workflow agent | Approval workflow escalation and threshold policy including risk/criticality-driven timeouts. |
| [approval_workflow.yaml](./approval_workflow.yaml) | the Approval Workflow agent | Approval workflow runtime toggles including delegation enablement and default delegation duration. |
| [business-case-settings.yaml](./business-case-settings.yaml) | the Business Case agent | Business case scoring weights, ROI thresholds, and template settings. |
| [risk_adjustments.yaml](./risk_adjustments.yaml) | the Risk Management agent | Risk scoring adjustment factors and severity thresholds. |
| [demo-participants.yaml](./demo-participants.yaml) | All (demo mode) | Demo participant configuration for local and demo environments. |

### Per-agent config directories

Complex agents with many config files use a dedicated subdirectory:

| Directory | Agent | Files |
| --- | --- | --- |
| [data-synchronisation-agent/](./data-synchronisation-agent/) | the Data Synchronisation agent – Data Sync | `mapping_rules.yaml`, `quality_thresholds.yaml`, `pipelines.yaml`, `schema_registry.yaml`, `validation_rules.yaml` |
| [approval-workflow-agent/](./approval-workflow-agent/) | Approval Workflow agent – workflow definitions and templates | `durable_workflows.yaml`, `workflow_templates.yaml` |

## Notes

**Intent routing — design vs runtime config:**
`intent-routing.yaml` in this directory is the canonical design reference. All agents use descriptive IDs (e.g. `risk-management-agent`). The live runtime config at `services/agent-runtime/src/config/intent-routing.yaml` should use the same descriptive IDs matching the IDs registered in `runtime.py`. Both files should be kept in sync for intent names and non-ID fields.

**Validation:**

```bash
python -m jsonschema -i ops/config/agents/intent-routing.yaml ops/config/agents/schema/intent-routing.schema.json
```

**Environment variable overrides:**

Most config values can be overridden via environment variables at runtime. Key overrides:

| Env var | Overrides | Default |
| --- | --- | --- |
| `INTENT_ROUTING_CONFIG_PATH` | the Intent Router agent routing config path | `ops/config/agents/intent-routing.yaml` |
| `DURABLE_WORKFLOW_CONFIG` | Approval Workflow agent durable workflows path | `ops/config/agents/approval-workflow-agent/durable_workflows.yaml` |
| `WORKFLOW_TEMPLATES_PATH` | Approval Workflow agent workflow templates path | `ops/config/agents/approval-workflow-agent/workflow_templates.yaml` |
