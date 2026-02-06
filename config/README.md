# Configuration

## Overview

This directory contains configuration assets consumed by services, agents, and the web console of the multi-agent PPM platform. Configuration is expressed as YAML and JSON files organized by domain.

## Directory structure

| Folder | Description |
| --- | --- |
| [abac/](./abac/) | Attribute-based access control policies |
| [agent-23/](./agent-23/) | Agent 23 specific configuration |
| [agent-24/](./agent-24/) | Agent 24 specific configuration |
| [agents/](./agents/) | Agent runtime and routing configuration (has schema/ subdir) |
| [connectors/](./connectors/) | Connector integration configuration |
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

- `config/abac/policies.yaml`: Attribute-based access control policies.
- `config/agents/*.yaml`: Agent runtime, intent routing, and domain agent configuration.
- `config/connectors/integrations.yaml`: Connector credentials, sync cadence, and field mapping overrides.
- `config/data-classification/levels.yaml`: Data classification tiers and retention bindings.
- `config/environments/*.yaml`: Environment-specific endpoints, vault references, and feature toggles.
- `config/feature-flags/flags.yaml`: Feature flag toggles by name.
- `config/rbac/*.yaml`: Roles, permissions, and field-level access rules.
- `config/retention/policies.yaml`: Retention policy definitions by classification.
- `config/security/dlp-policies.yaml`: DLP policy thresholds and enforcement actions.
- `config/signing/`: Signing metadata for artifacts and images.
- `config/tenants/default.yaml`: Default tenant bootstrap configuration.

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
| `<connector>.sync.*` | Sync cadence (`interval_minutes`), entities, and enablement. |
| `<connector>.field_mapping.*` | Canonical → source field overrides. |
| `<connector>.features.*` | Optional features such as notifications or interactive messages. |
| `integration_defaults.retry_policy.*` | Default retry behavior for connector runtime. |
| `integration_defaults.timeout_seconds` | Network timeout defaults. |
| `integration_defaults.rate_limiting.*` | Rate limiting config for sync operations. |
| `integration_defaults.error_handling.*` | Logging, alerting, and circuit breaker settings. |

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
