# Configuration

## Overview

This directory contains configuration assets consumed by services, agents, and the web console of the multi-agent PPM platform. Configuration is expressed as YAML and JSON files organized by domain.

## Directory structure

| Folder | Description |
| --- | --- |
| [abac/](./abac/) | Attribute-based access control policies |
| [data-synchronisation-agent/](./data-synchronisation-agent/) | the Data Synchronisation agent specific configuration |
| [workflow-engine-agent/](./workflow-engine-agent/) | the Workflow Engine agent specific configuration |
| [agents/](./agents/) | Agent runtime and routing configuration (has schema/ subdir) |
| [integrations/connectors/](../../integrations/connectors/) | Connector integration configuration |
| [data-classification/](./data-classification/) | Data classification levels |
| [environments/](./environments/) | Environment-specific settings (dev, test, prod) |
| [feature-flags/](./feature-flags/) | Feature flag toggles |
| [iam/](./iam/) | IAM role mapping |
| [rbac/](./rbac/) | Role-based access control |
| [retention/](./retention/) | Data retention policies |
| [security/](./security/) | DLP and security policies |
| [signing/](./signing/) | Artifact signing metadata |
| [tenants/](./tenants/) | Tenant configuration |

## What's inside

- [policies.yaml](/config/abac/policies.yaml): Attribute-based access control policies.
- [*.yaml](/config/agents/*.yaml): Agent runtime, intent routing, and domain agent configuration.
- [integrations.yaml](/config/connectors/integrations.yaml): Connector credentials, sync cadence, and field mapping overrides.
- [levels.yaml](/config/data-classification/levels.yaml): Data classification tiers and retention bindings.
- [*.yaml](/config/environments/*.yaml): Environment-specific endpoints, vault references, and feature toggles.
- [flags.yaml](/config/feature-flags/flags.yaml): Feature flag toggles by name.
- [*.yaml](/config/rbac/*.yaml): Roles, permissions, and field-level access rules.
- [policies.yaml](/config/retention/policies.yaml): Retention policy definitions by classification.
- [dlp-policies.yaml](/config/security/dlp-policies.yaml): DLP policy thresholds and enforcement actions.
- [](/config/signing/): Signing metadata for artifacts and images.
- [default.yaml](/config/tenants/default.yaml): Default tenant bootstrap configuration.
- [vector_store.yaml](/config/vector_store.yaml): Vector store shard, FAISS, cache, batch, and TTL settings.

## How it's used

Configuration files are loaded by apps, services, and agents at runtime. Most services read from `.env` or secret managers first, then fall back to YAML defaults in `config/` when available.

## Configuration field reference

### `config/agents/portfolio.yaml`

Defines domain agent behavior for demand intake, business case generation, portfolio strategy, and program management.

| Field | Description |
| --- | --- |
| `demand_intake.agent_id` | Stable identifier for the demand intake agent. |
| `demand_intake.enabled` | Enable or disable the agent. |
| `demand_intake.similarity_threshold` | Similarity score threshold for duplicate detection. |
| `demand_intake.mandatory_fields` | Fields required before a demand record is accepted. |
| `demand_intake.auto_categorization.model` | LLM provider and deployment for auto-categorisation. |
| `demand_intake.duplicate_detection.search_provider` | Search backend used for similarity lookups. |
| `demand_intake.notification.channels` | Notification targets (`email`, `teams`). |
| `business_case.roi_calculation.*` | Financial model settings for ROI analysis. |
| `business_case.financial_models` | ROI models to run (NPV, IRR, etc.). |
| `portfolio_strategy.optimization.*` | Multi-objective optimisation algorithm and tuning. |
| `portfolio_strategy.criteria_weights` | Weighted scoring for portfolio ranking. |
| `portfolio_strategy.rebalancing.*` | Rebalancing cadence and thresholds. |
| `program_management.dependency_tracking.*` | Dependency tracking and conflict detection settings. |
| `program_management.benefits_realization.*` | Benefits tracking cadence and variance threshold. |

### `config/agents/orchestration.yaml`

Controls the intent router and response orchestration agents.

| Field | Description |
| --- | --- |
| `intent_router.agent_id` | Identifier for the intent router agent. |
| `intent_router.model.*` | LLM provider, deployment, and generation parameters. |
| `intent_router.intents` | Allowed intent names mapped in `config/agents/intent-routing.yaml`. |
| `intent_router.confidence_threshold` | Minimum confidence required to accept a routed intent. |
| `response_orchestration.max_concurrency` | Parallel agent calls per request. |
| `response_orchestration.agent_timeout` | Timeout (seconds) for downstream agents. |
| `response_orchestration.cache_ttl` | Cache duration (seconds) for orchestration results. |
| `response_orchestration.retry_policy.*` | Retry backoff settings for failed agents. |
| `response_orchestration.fallback_policy` | Behavior on partial failures (`fail_fast`, `partial_return`, `block`). |
| `response_orchestration.aggregation.*` | LLM settings for final response synthesis. |

### `config/agents/intent-routing.yaml`

Defines intent routing rules and the agent/action targets per intent.

| Field | Description |
| --- | --- |
| `version` | Routing schema version. |
| `default_min_confidence` | Default confidence threshold if an intent does not specify one. |
| `fallback_intent` | Intent used when classification confidence is low. |
| `intents[].name` | Intent identifier used by the router. |
| `intents[].routes[].agent_id` | Target agent registered in the agent runtime. |
| `intents[].routes[].action` | Agent action invoked for the intent. |
| `intents[].routes[].dependencies` | Dependencies to resolve before invoking the agent. |

### `config/connectors/integrations.yaml`

Connector configuration and sync defaults.

| Field | Description |
| --- | --- |
| `<connector>.enabled` | Enable the connector instance. |
| `<connector>.base_url` / `<connector>.instance_url` | Base URL for API calls. |
| `<connector>.auth.*` | Authentication type and credential fields. |
| `<connector>.mcp.*` | Optional MCP server block (`server_id`, `server_url`, `client_id`, `client_secret`, `auth_scopes`, `tool_map`, `tools`) for MCP routing defaults. |
| `<connector>.sync.*` | Sync cadence (`interval_minutes`), entities, and enablement. |
| `<connector>.field_mapping.*` | Canonical → source field overrides. |
| `<connector>.features.*` | Optional features such as notifications or interactive messages. |
| `integration_defaults.retry_policy.*` | Default retry behavior for connector runtime. |
| `integration_defaults.timeout_seconds` | Network timeout defaults. |
| `integration_defaults.rate_limiting.*` | Rate limiting config for sync operations. |
| `integration_defaults.error_handling.*` | Logging, alerting, and circuit breaker settings. |

## MCP connectors

MCP-enabled connectors can be configured to route requests through an MCP server instead of calling the upstream API directly. Each connector in `config/connectors/integrations.yaml` now includes an optional `mcp` block with defaults like `server_id: mcp_<connector>`, `server_url: https://mcp.example.com/<connector>`, `auth_scopes` for OAuth-backed MCP servers, a `tool_map` for canonical → MCP tool routing, and a starter `tools` map (for example `projects` and `work_items`). Add the MCP server settings in `.env` and set the matching `<CONNECTOR>_PREFER_MCP=true` flag when you want the connector runtime to prefer MCP. Most MCP servers use OAuth client credentials, so provide the MCP client ID and secret when required by the connector.

| Connector ID | MCP server URL env var | OAuth MCP credentials (if required) | Notes |
| --- | --- | --- | --- |
| `planview` | `PLANVIEW_MCP_SERVER_URL` | `PLANVIEW_MCP_CLIENT_ID`, `PLANVIEW_MCP_CLIENT_SECRET` | Enable with `PLANVIEW_PREFER_MCP=true`. |
| `clarity` | `CLARITY_MCP_SERVER_URL` | `CLARITY_MCP_CLIENT_ID`, `CLARITY_MCP_CLIENT_SECRET` | Enable with `CLARITY_PREFER_MCP=true`. |
| `jira` | `JIRA_MCP_SERVER_URL` | `JIRA_MCP_CLIENT_ID`, `JIRA_MCP_CLIENT_SECRET` (only if your MCP server uses OAuth) | Enable with `JIRA_PREFER_MCP=true`. |
| `azure_devops` | `AZURE_DEVOPS_MCP_SERVER_URL` | `AZURE_DEVOPS_MCP_CLIENT_ID`, `AZURE_DEVOPS_MCP_CLIENT_SECRET` (only if your MCP server uses OAuth) | Enable with `AZURE_DEVOPS_PREFER_MCP=true`. |
| `sap` | `SAP_MCP_SERVER_URL` | `SAP_MCP_CLIENT_ID`, `SAP_MCP_CLIENT_SECRET` | Enable with `SAP_PREFER_MCP=true`. |
| `workday` | `WORKDAY_MCP_SERVER_URL` | `WORKDAY_MCP_CLIENT_ID`, `WORKDAY_MCP_CLIENT_SECRET` | Enable with `WORKDAY_PREFER_MCP=true`. |
| `slack` | `SLACK_MCP_SERVER_URL` | `SLACK_MCP_CLIENT_ID`, `SLACK_MCP_CLIENT_SECRET` | Enable with `SLACK_PREFER_MCP=true`. |
| `teams` | `TEAMS_MCP_SERVER_URL` | `TEAMS_MCP_CLIENT_ID`, `TEAMS_MCP_CLIENT_SECRET` | Enable with `TEAMS_PREFER_MCP=true`. |
| `outlook` | `OUTLOOK_MCP_SERVER_URL` | `OUTLOOK_MCP_CLIENT_ID`, `OUTLOOK_MCP_CLIENT_SECRET` | Enable with `OUTLOOK_PREFER_MCP=true`. |
| `google_calendar` | `GOOGLE_CALENDAR_MCP_SERVER_URL` | `GOOGLE_CALENDAR_MCP_CLIENT_ID`, `GOOGLE_CALENDAR_MCP_CLIENT_SECRET` | Enable with `GOOGLE_CALENDAR_PREFER_MCP=true`. |
| `smartsheet` | `SMARTSHEET_MCP_SERVER_URL` | `SMARTSHEET_MCP_CLIENT_ID`, `SMARTSHEET_MCP_CLIENT_SECRET` (only if your MCP server uses OAuth) | Enable with `SMARTSHEET_PREFER_MCP=true`. |
| `sharepoint` | `SHAREPOINT_MCP_SERVER_URL` | `SHAREPOINT_MCP_CLIENT_ID`, `SHAREPOINT_MCP_CLIENT_SECRET` | Enable with `SHAREPOINT_PREFER_MCP=true`. |
| `salesforce` | `SALESFORCE_MCP_SERVER_URL` | `SALESFORCE_MCP_CLIENT_ID`, `SALESFORCE_MCP_CLIENT_SECRET` | Enable with `SALESFORCE_PREFER_MCP=true`. |
| `asana` | `ASANA_MCP_SERVER_URL` | `ASANA_MCP_CLIENT_ID`, `ASANA_MCP_CLIENT_SECRET` (only if your MCP server uses OAuth) | Enable with `ASANA_PREFER_MCP=true`. |
| `azure_communication_services` | `AZURE_COMMUNICATION_SERVICES_MCP_SERVER_URL` | `AZURE_COMMUNICATION_SERVICES_MCP_CLIENT_ID`, `AZURE_COMMUNICATION_SERVICES_MCP_CLIENT_SECRET` (only if your MCP server uses OAuth) | Enable with `AZURE_COMMUNICATION_SERVICES_PREFER_MCP=true`. |
| `twilio` | `TWILIO_MCP_SERVER_URL` | `TWILIO_MCP_CLIENT_ID`, `TWILIO_MCP_CLIENT_SECRET` (only if your MCP server uses OAuth) | Enable with `TWILIO_PREFER_MCP=true`. |
| `notification_hubs` | `AZURE_NOTIFICATION_HUBS_MCP_SERVER_URL` | `AZURE_NOTIFICATION_HUBS_MCP_CLIENT_ID`, `AZURE_NOTIFICATION_HUBS_MCP_CLIENT_SECRET` (only if your MCP server uses OAuth) | Enable with `AZURE_NOTIFICATION_HUBS_PREFER_MCP=true`. |

### Managing MCP OAuth secrets in Key Vault and Secrets Manager

For production deployments, store MCP OAuth client IDs/secrets in a managed secret store and map them to the runtime environment variables consumed by the connector runtime. Follow the production guidance in [ADR 0010](../docs/architecture/adr/0010-secrets-management.md) for managed secret rotation and local `.env` usage.

**Azure Key Vault**

1. Create Key Vault secrets using the same key names as the env vars (recommended) or document a mapping table.
2. Use the Kubernetes SecretProviderClass (or your preferred runtime injector) to project those secrets as environment variables.

Example mapping (recommended: keep names identical):

| Key Vault secret name | Runtime env var |
| --- | --- |
| `PLANVIEW_MCP_CLIENT_ID` | `PLANVIEW_MCP_CLIENT_ID` |
| `PLANVIEW_MCP_CLIENT_SECRET` | `PLANVIEW_MCP_CLIENT_SECRET` |
| `PLANVIEW_MCP_SERVER_URL` | `PLANVIEW_MCP_SERVER_URL` |

**AWS Secrets Manager**

1. Store secrets as either discrete entries (one per env var) or a single JSON secret.
2. Configure your runtime (ECS task definition, Kubernetes External Secrets, etc.) to map the secret keys to environment variables.

Example mapping (single JSON secret named `mcp/planview`):

| Secrets Manager key | Runtime env var |
| --- | --- |
| `PLANVIEW_MCP_CLIENT_ID` | `PLANVIEW_MCP_CLIENT_ID` |
| `PLANVIEW_MCP_CLIENT_SECRET` | `PLANVIEW_MCP_CLIENT_SECRET` |
| `PLANVIEW_MCP_SERVER_URL` | `PLANVIEW_MCP_SERVER_URL` |

For local development, continue to use `.env` files that are excluded from source control, and only reference cloud secret managers in shared environments. See [ADR 0010](../docs/architecture/adr/0010-secrets-management.md) for the production versus local development split.

### `config/environments/*.yaml`

Environment-specific endpoints, secrets, and feature toggles.

| Field | Description |
| --- | --- |
| `name` | Environment label (`dev`, `test`, `prod`). |
| `region` | Region identifier for production environments. |
| `endpoints.*` | Secret references for platform service URLs. |
| `vault.uri` | Secret manager base URI. |
| `vault.secrets.*` | Secret references used by platform components. |
| `feature_flags.*` | Environment-level feature toggles. |
| `observability.*` | OpenTelemetry and log level settings. |
| `connectors.*` | Secret references for connector credentials. |
| `databases.*` | Database connection strings (primary, analytics). |
| `service_bus.*` | Service Bus connection strings, queues, and topics. |
| `graph_api.*` | Microsoft Graph API configuration. |
| `email.*` | Email provider configuration (SMTP/SendGrid). |

### `config/feature-flags/flags.yaml`

Defines global feature flags. Each entry in `flags` supports:

| Field | Description |
| --- | --- |
| `name` | Feature flag identifier. |
| `enabled` | Boolean toggle for the feature. |
| `description` | Human-readable intent for the flag. |

MCP rollout flags use the naming convention `mcp_global_enabled`, `mcp_system_<system>`,
and `mcp_project_<project_id>`. Project flags override system flags, and system flags
override the global default.

### `config/tenants/default.yaml`

Default tenant bootstrap configuration (see `config/tenants/README.md`).

### `config/rbac/*.yaml`

RBAC roles, permissions, and field-level access rules.

| File | Key fields |
| --- | --- |
| `roles.yaml` | `roles[].id`, `roles[].description`, `roles[].permissions` |
| `permissions.yaml` | `permissions[].id`, `permissions[].description` |
| `field-level.yaml` | `fields.<entity>.<field>.allowed_roles`, `classification_access.<level>.allowed_roles` |

### `config/abac/policies.yaml`

Attribute-based access policies.

| Field | Description |
| --- | --- |
| `default_decision` | Default decision if no policy matches. |
| `policies[].id` | Policy identifier. |
| `policies[].effect` | `allow` or `deny` on match. |
| `policies[].rules` | Rule list with `field`, `operator`, and `value`/`value_from`. |

### `config/data-classification/levels.yaml`

| Field | Description |
| --- | --- |
| `levels[].id` | Classification level (`public`, `internal`, etc.). |
| `levels[].description` | Human-readable description. |
| `levels[].retention_policy` | Retention policy ID from `config/retention/policies.yaml`. |
| `levels[].allowed_roles` | Roles allowed to access that classification. |

### `config/retention/policies.yaml`

| Field | Description |
| --- | --- |
| `policies[].id` | Retention policy identifier. |
| `policies[].description` | Summary of retention intent. |
| `policies[].duration_days` | Retention window in days. |
| `policies[].storage_class` | Storage tier for data after ingestion. |

### `config/security/dlp-policies.yaml`

| Field | Description |
| --- | --- |
| `version` | DLP policy schema version. |
| `classifications.*` | Advisory/deny thresholds per classification level. |
| `finding_enforcement.*` | Action per detected pattern (`block`, `advisory`). |

## How to run / develop / test

Review configuration files directly before running services.

## Configuration

Edit the relevant YAML/JSON files and update `.env` values as needed.

## Troubleshooting

- Config not applied: ensure the runtime points to the correct file.
- Schema errors: validate configuration format with `python scripts/check-placeholders.py`.

### `config/pricing.yaml`

Defines pricing inputs for cost tracking.

| Field | Description |
| --- | --- |
| `llm_models.<model>.input_per_1k_tokens_usd` | Input token price used for connector LLM cost estimation. |
| `llm_models.<model>.output_per_1k_tokens_usd` | Output token price used for connector LLM cost estimation. |
| `connectors.default.cost_per_call_usd` | Default external API cost per connector call. |
| `connectors.<connector>.cost_per_call_usd` | Connector-specific call cost override. |
| `connectors.<connector>.cost_per_resource_usd` | Optional endpoint/resource-level additive pricing. |
