# Connectors

> Comprehensive reference for connector architecture, authentication patterns, data mapping, certification, maturity rubric, Microsoft 365 field mappings, IoT specification, and Model Context Protocol (MCP) server configuration, development, onboarding, coverage, and release readiness across all 38 integrations in the Multi-Agent PPM Platform.

## Contents

- [Overview](#overview)
- [Supported Systems](#supported-systems)
- [Authentication Patterns](#authentication-patterns)
- [Data Mapping](#data-mapping)
- [REST Connector Configuration](#rest-connector-configuration)
- [Connector Certification](#connector-certification)
- [Maturity Rubric](#maturity-rubric)
- [Microsoft 365 Field Mappings](#microsoft-365-field-mappings)
- [IoT Connector Specification](#iot-connector-specification)
- [MCP Server Configuration](#mcp-server-configuration)
- [MCP Connector Development](#mcp-connector-development)
- [MCP Connector Onboarding](#mcp-connector-onboarding)
- [MCP Coverage Matrix](#mcp-coverage-matrix)
- [MCP Release Checklist](#mcp-release-checklist)

---

## Overview

### Purpose

Define how the Multi-Agent PPM Platform integrates with enterprise systems, including authentication, canonical mapping, sync strategy, conflict resolution, and connector certification.

### Architecture-level context

Connectors sit between domain agents and external systems of record. They translate canonical schemas in `data/schemas/` into system-specific payloads, enforce auth policies, and emit lineage/quality metadata for every sync. Connector metadata is stored in the registry at `connectors/registry/`.

The platform uses the Model Context Protocol (MCP), a JSON-RPC protocol that exposes tools, resources, and prompts to AI applications. MCP servers act as the registry and execution layer for connector tools, while REST fallbacks remain available when MCP coverage is incomplete.

### Connector lifecycle

1. **Register**: add a manifest in `connectors/<name>/manifest.yaml` and list it in `connectors/registry/connectors.json`.
2. **Map**: create mapping YAMLs under `connectors/<name>/mappings/` for each entity.
3. **Authenticate**: configure auth profile based on `connectors/registry/schemas/auth-config.schema.json`.
4. **Sync**: use the connector runner to pull/push canonical entities.
5. **Certify**: execute the certification checklist and attach evidence.

### Authentication patterns

- **OAuth 2.0 / OIDC** (preferred): configured per connector with refresh token handling.
- **API tokens**: stored in vault and scoped to the connector.
- **Service accounts**: for systems that only support basic auth.

Auth configuration lives in environment-specific files under `ops/config/` and is referenced by connector manifests.

### Project-level configuration

REST connector configurations are stored per PPM project using `ProjectConnectorConfigStore`, including non-secret fields like `instance_url` and `project_key` plus secrets sourced from environment variables. See the [REST Connector Configuration](#rest-connector-configuration) section for the full per-connector field list.

### Mapping approach

Mappings are declarative YAML that map canonical fields to external system fields. The mapping engine applies transformations (enum, date, currency) and emits quality scores.

**Example mapping file**: `connectors/jira/mappings/project.yaml`

### Sync strategy and conflict resolution

- **Sync modes**: read-only, write-only, bi-directional.
- **Incremental sync**: change data capture based on updated timestamps.
- **Conflict resolution**: configurable policies (source-wins, platform-wins, manual review).

Connector sync telemetry is recorded as lineage artifacts under `data/lineage/`.

### Certification process

The [Connector Certification](#connector-certification) section includes:

- Schema validation and mapping coverage
- Auth and rate-limit handling
- Functional tests in sandbox environments
- Security review and secrets handling

### Diagram

```text
PlantUML: docs/architecture/diagrams/seq-connector-sync.puml
```

### Usage example

Inspect the Jira connector manifest:

```bash
sed -n '1,120p' connectors/jira/manifest.yaml
```

### How to verify

Validate the connector registry lists Jira:

```bash
rg -n "jira" connectors/registry/connectors.json
```

Expected output: a JSON entry for Jira with a manifest path.

### Implementation status

- **Implemented**: connector runtime logic, OAuth2 refresh handling, and registry coverage for Jira, Planview, Clarity, ServiceNow, and SAP.
- **In progress**: register and certify the remaining packaged connectors (Azure DevOps, Salesforce, SharePoint, Slack, Teams, Workday).

---

## Supported Systems

### Purpose

List connector coverage and maturity based on the current connector registry and packaged connector assets.

### Status definitions

- **production**: Certified connector with automated tests and runtime support.
- **beta**: Functional connector package with runtime support and in-progress certification.

### Connector coverage

The full list of supported systems, their categories, and MCP/REST coverage is derived from connector manifests. View it via the generated registry:

```bash
python -c "import json; [print(f\"{c['id']:30s} {c['category']:15s} {c['status']}\" ) for c in json.load(open('connectors/registry/connectors.json'))]"
```

To check which systems have MCP counterparts, look for connectors whose manifest contains `protocol: mcp` and compare by `system` field.

### Registry status (runtime-ready)

The authoritative registry list lives in `connectors/registry/connectors.json` and is generated from connector manifests by `connectors/registry/generate.py`. Do not edit the JSON file by hand — regenerate it instead:

```bash
python connectors/registry/generate.py
```

### Verification steps

- View the registry:
  ```bash
  cat connectors/registry/connectors.json
  ```
- Check for connector manifests:
  ```bash
  ls connectors/*/manifest.yaml
  ```

### Implementation status

- **Implemented:** Connector registry now includes every packaged connector.
- **Implemented:** All listed connector packages include manifests and runtime mappings.

---

## Authentication Patterns

### Purpose

Document the authentication patterns supported by connector manifests and configuration files.

### Configuration sources

- Connector manifests (`connectors/<name>/manifest.yaml`) specify the auth type expected by the connector.
- Environment-specific configuration is stored in `ops/config/connectors/integrations.yaml` and references secrets via environment variables.
- Auth schema guidance lives in `connectors/registry/schemas/auth-config.schema.json`.

### Supported patterns

| Auth type | Description | Example connector |
| --- | --- | --- |
| `oauth2` | OAuth 2.0 client credentials or auth code flows | SAP, Workday |
| `api_token` | Static API token with optional email/user | Jira |
| `pat` | Personal access token | Azure DevOps |
| `bot_token` | Bot tokens for chat integrations | Slack |
| `app_credentials` | App registration credentials (client id/secret) | Teams |
| `azure_ad` | Azure AD-based integration | SharePoint |

### MCP connector authentication

MCP-enabled connectors can delegate authentication to an MCP server. Configure the MCP server URL and ID in `.env` (for example, `SLACK_MCP_SERVER_URL`, `TEAMS_MCP_SERVER_URL`) and supply MCP OAuth client credentials when the MCP server expects OAuth (`*_MCP_CLIENT_ID`, `*_MCP_CLIENT_SECRET`). Set `<CONNECTOR>_PREFER_MCP=true` to route connector traffic through MCP for the matching connector ID.

### Storing MCP OAuth secrets in managed secret stores

Use managed secret stores in production and map secret values to the environment variables expected by MCP connectors. Local development can rely on a `.env` file (kept out of source control). See [ADR 0010](../architecture/adr/0010-secrets-management.md) for the production practices and local development split.

#### Azure Key Vault

- Create Key Vault secrets that match the env var names, or define explicit mappings if you need different naming.
- Use SecretProviderClass or your runtime injector to expose the secrets as environment variables.

Example mapping (Key Vault secret → env var):

| Key Vault secret name | Runtime env var |
| --- | --- |
| `PLANVIEW_MCP_CLIENT_ID` | `PLANVIEW_MCP_CLIENT_ID` |
| `PLANVIEW_MCP_CLIENT_SECRET` | `PLANVIEW_MCP_CLIENT_SECRET` |
| `PLANVIEW_MCP_SERVER_URL` | `PLANVIEW_MCP_SERVER_URL` |

#### AWS Secrets Manager

- Store secrets as discrete entries or a single JSON secret.
- Configure your runtime to map keys to env vars (ECS task definition, Kubernetes External Secrets, etc.).

Example mapping (JSON secret `mcp/planview` → env var):

| Secrets Manager key | Runtime env var |
| --- | --- |
| `PLANVIEW_MCP_CLIENT_ID` | `PLANVIEW_MCP_CLIENT_ID` |
| `PLANVIEW_MCP_CLIENT_SECRET` | `PLANVIEW_MCP_CLIENT_SECRET` |
| `PLANVIEW_MCP_SERVER_URL` | `PLANVIEW_MCP_SERVER_URL` |

### Operational guidance

1. Store secrets in your secret manager and inject via env vars.
2. Update `ops/config/connectors/integrations.yaml` with the secret references.
3. Ensure manifests and mappings are registered in `connectors/registry/connectors.json` before enabling the connector.

### Verification steps

- Inspect the integration configuration:
  ```bash
  sed -n '1,200p' ops/config/connectors/integrations.yaml
  ```
- Validate connector manifest auth sections:
  ```bash
  rg -n "auth:" connectors/*/manifest.yaml
  ```

### Implementation status

- **Implemented:** Manifest auth definitions, environment configuration structure.
- **Implemented:** OAuth refresh token management with optional Key Vault rotation support.

---

## Data Mapping

### Purpose

Describe how connector mappings translate source-system records into the platform's canonical schemas.

### Mapping model

Each connector includes:

- A manifest (`connectors/<name>/manifest.yaml`) listing mappings and sync settings.
- Mapping files under `connectors/<name>/mappings/` describing field-level transformations.
- Runtime logic via the connector SDK (`connectors/sdk/src/runtime.py`).

### Mapping flow

1. **Load manifest:** Connector runtime loads and validates the manifest against `connectors/registry/schemas/connector-manifest.schema.json`.
2. **Load mapping specs:** Each mapping file defines `source`, `target`, and a list of field mappings.
3. **Apply mapping:** Records are transformed into canonical fields and enriched with `tenant_id`.

### Example mapping

```yaml
source: project
schema: project
target: project
fields:
  - source: id
    target: id
  - source: name
    target: name
```

Example file: `connectors/jira/mappings/project.yaml`.

### Validation guidance

- Ensure mapping targets exist in `data/schemas/*.schema.json`.
- Run mapping validation using connector fixtures.
  - For registry-listed connectors, run `python ops/scripts/connector-certification.py` to validate required target fields.

Example dry-run with Jira fixtures:

```bash
python -m integrations.connectors.jira.src.main connectors/jira/tests/fixtures/projects.json --tenant dev-tenant
```

### Implementation status

- **Implemented:** Connector SDK runtime, manifest validation, mapping application, and automated mapping coverage checks.
- **Implemented:** Advanced transformations (lookups, enums, date conversions) and quality scoring integration.

---

## REST Connector Configuration

### Purpose

Document configuration expectations for REST-backed connectors, including project-level configuration and the fields each connector expects.

### Project-level configuration

REST connectors are configured per PPM project using `ProjectConnectorConfigStore`, which persists to `data/connectors/project_config.json`. Each stored configuration includes:

- `ppm_project_id` to scope the connector configuration to a single PPM project.
- Standard connector metadata (`connector_id`, `name`, `category`, sync settings).
- Connector-specific non-secret fields (for example, `instance_url`, `project_key`).
- Secret values sourced from environment variables or secret managers, as listed below.

### OAuth rotation fields

OAuth 2.0 connectors support additional optional fields:

- `rotation_enabled`
- `rotation_provider`
- `refresh_token_rotation_days`
- `client_secret_rotation_days`

### REST connector configuration matrix

| Connector ID | Auth Type | Non-secret config fields | Environment variables / secrets |
| --- | --- | --- | --- |
| planview | oauth2 | `instance_url`, `portfolio_id`, OAuth rotation fields | `PLANVIEW_INSTANCE_URL`, `PLANVIEW_CLIENT_ID`, `PLANVIEW_CLIENT_SECRET`, `PLANVIEW_REFRESH_TOKEN` |
| clarity | oauth2 | `instance_url`, OAuth rotation fields | `CLARITY_INSTANCE_URL`, `CLARITY_CLIENT_ID`, `CLARITY_CLIENT_SECRET`, `CLARITY_REFRESH_TOKEN` |
| ms_project_server | oauth2 | `tenant_id`, `site_url`, OAuth rotation fields | `MS_PROJECT_TENANT_ID`, `MS_PROJECT_SITE_URL`, `MS_PROJECT_CLIENT_ID`, `MS_PROJECT_CLIENT_SECRET`, `MS_PROJECT_REFRESH_TOKEN` |
| jira | api_key | `instance_url`, `project_key` | `JIRA_INSTANCE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` |
| azure_devops | api_key | `organization_url`, `project_name` | `AZURE_DEVOPS_ORG_URL`, `AZURE_DEVOPS_PAT` |
| monday | api_key | `instance_url`, `board_ids` | `MONDAY_API_TOKEN` |
| asana | oauth2 | `instance_url`, `workspace_gid`, OAuth rotation fields | `ASANA_ACCESS_TOKEN` |
| sharepoint | oauth2 | `site_url`, `document_library`, OAuth rotation fields | `SHAREPOINT_SITE_URL`, `SHAREPOINT_CLIENT_ID`, `SHAREPOINT_CLIENT_SECRET`, `SHAREPOINT_REFRESH_TOKEN` |
| confluence | basic | `instance_url`, `space_key` | `CONFLUENCE_URL`, `CONFLUENCE_EMAIL`, `CONFLUENCE_API_TOKEN` |
| google_drive | oauth2 | `instance_url`, `folder_id`, OAuth rotation fields | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` |
| sap | basic | `instance_url`, `client_id` | `SAP_URL`, `SAP_USERNAME`, `SAP_PASSWORD`, `SAP_CLIENT` |
| oracle | oauth2 | `instance_url`, OAuth rotation fields | `ORACLE_URL`, `ORACLE_CLIENT_ID`, `ORACLE_CLIENT_SECRET`, `ORACLE_REFRESH_TOKEN` |
| netsuite | oauth2 | `instance_url`, `account_id`, OAuth rotation fields | `NETSUITE_ACCOUNT_ID`, `NETSUITE_CONSUMER_KEY`, `NETSUITE_CONSUMER_SECRET`, `NETSUITE_REFRESH_TOKEN` |
| workday | oauth2 | `instance_url`, `tenant_name`, OAuth rotation fields | `WORKDAY_API_URL`, `WORKDAY_CLIENT_ID`, `WORKDAY_CLIENT_SECRET`, `WORKDAY_REFRESH_TOKEN` |
| sap_successfactors | oauth2 | `api_server`, `company_id`, OAuth rotation fields | `SF_API_SERVER`, `SF_COMPANY_ID`, `SF_CLIENT_ID`, `SF_CLIENT_SECRET`, `SF_REFRESH_TOKEN` |
| adp | oauth2 | OAuth rotation fields | `ADP_API_URL`, `ADP_CLIENT_ID`, `ADP_CLIENT_SECRET`, `ADP_REFRESH_TOKEN` |
| teams | oauth2 | `instance_url`, `team_id`, `channel_id`, OAuth rotation fields | `TEAMS_CLIENT_ID`, `TEAMS_CLIENT_SECRET`, `TEAMS_REFRESH_TOKEN`, `TEAMS_TENANT_ID` |
| slack | oauth2 | `instance_url`, `workspace_id`, `default_channel`, OAuth rotation fields | `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET` |
| zoom | oauth2 | OAuth rotation fields | `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET`, `ZOOM_REFRESH_TOKEN` |
| servicenow_grc | oauth2 | `instance_url`, OAuth rotation fields | `SERVICENOW_URL`, `SERVICENOW_CLIENT_ID`, `SERVICENOW_CLIENT_SECRET`, `SERVICENOW_REFRESH_TOKEN` |
| archer | api_key | `instance_url` | `ARCHER_URL`, `ARCHER_API_KEY` |
| logicgate | api_key | `instance_url`, `subdomain` | `LOGICGATE_API_URL`, `LOGICGATE_API_KEY` |
| regulatory_compliance | api_key | `endpoint_url`, `api_key`, `supported_regulations` | `REGULATORY_COMPLIANCE_ENDPOINT`, `REGULATORY_COMPLIANCE_API_KEY` |
| iot | api_key | `protocol`, `device_endpoint`, `auth_token`, `device_ids`, `sensor_types`, `mqtt_broker`, `mqtt_port`, `mqtt_username`, `mqtt_password`, `mqtt_topic`, `poll_interval_seconds` | `IOT_PROTOCOL`, `IOT_DEVICE_ENDPOINT`, `IOT_AUTH_TOKEN`, `IOT_DEVICE_IDS`, `IOT_SENSOR_TYPES`, `IOT_MQTT_BROKER`, `IOT_MQTT_PORT`, `IOT_MQTT_USERNAME`, `IOT_MQTT_PASSWORD`, `IOT_MQTT_TOPIC`, `IOT_POLL_INTERVAL_SECONDS` |
| azure_communication_services | api_key | `endpoint` | `AZURE_COMMUNICATION_ENDPOINT`, `AZURE_COMMUNICATION_KEY` |
| google_calendar | oauth2 | `calendar_id`, OAuth rotation fields | `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET`, `GOOGLE_CALENDAR_REFRESH_TOKEN` |
| m365 | oauth2 | `tenant_id`, OAuth rotation fields | `M365_TENANT_ID`, `M365_CLIENT_ID`, `M365_CLIENT_SECRET` |
| notification_hubs | token | `namespace`, `hub_name` | `NOTIFICATION_HUBS_CONNECTION_STRING` |
| outlook | oauth2 | `tenant_id`, OAuth rotation fields | `OUTLOOK_CLIENT_ID`, `OUTLOOK_CLIENT_SECRET`, `OUTLOOK_REFRESH_TOKEN`, `OUTLOOK_TENANT_ID` |
| salesforce | oauth2 | `instance_url`, OAuth rotation fields | `SALESFORCE_INSTANCE_URL`, `SALESFORCE_CLIENT_ID`, `SALESFORCE_CLIENT_SECRET`, `SALESFORCE_REFRESH_TOKEN` |
| smartsheet | api_key | `instance_url` | `SMARTSHEET_API_TOKEN` |
| twilio | basic | `account_sid` | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` |

### MCP monitoring

When a vendor or marketplace announces an MCP server for a REST connector, update the connector classification to add an MCP entry in the registry, mark `mcp_preferred` when appropriate, and keep the REST connector available as a fallback for project-level configurations.

For MCP server auth, scopes, and tool mapping guidance, see [MCP Server Configuration](#mcp-server-configuration).

---

## Connector Certification

### Purpose

Define the certification workflow required before a connector can be enabled in production environments.

### Architecture-level context

Certification ensures connectors enforce the same security, data quality, and operational standards as the core platform. Evidence is attached to the connector registry and referenced by the orchestration layer before a connector can be activated.

### Certification checklist

| Step | Evidence | Artifact path |
| --- | --- | --- |
| Schema coverage | Mapping files cover required fields | `connectors/<name>/mappings/*.yaml` |
| Auth validation | Token flow tested and rotated | `ops/config/<env>/connector-auth.yaml` |
| Sandbox tests | CRUD against vendor sandbox | `connectors/<name>/tests/` |
| Rate-limit handling | Retry policy documented | `connectors/<name>/manifest.yaml` |
| Security review | Secrets stored in vault | `docs/architecture/security-architecture.md` |
| Data lineage | Lineage artifact emitted | `data/lineage/` |

### Usage example

Record certification status in the registry:

```bash
rg -n "certification" connectors/registry/connectors.json
```

### How to verify

Ensure a connector has at least one mapping file:

```bash
ls connectors/jira/mappings
```

Expected output: mapping files such as `project.yaml`.

### Certification automation

Run the automated certification harness to validate manifests, mapping coverage, and contract tests. The command emits a report artifact used by CI:

```bash
python ops/scripts/connector-certification.py --output artifacts/connector-certification-report.json --run-tests
```

The report includes per-connector results plus a summary status.

### Implementation status

- **Implemented**: automated certification evidence collection and report generation.
- **Maintained**: manual checklist and registry metadata for audit context.

---

## Maturity Rubric

This rubric defines implementation expectations for connector manifests (`connectors/*/manifest.yaml`) and CI quality gates.

### Level definitions

#### Level 0 — Registered only

- Manifest exists and validates.
- Connector can be discovered/loaded.
- No guaranteed read/write/webhook support.

#### Level 1 — Read-ready

- Level 0 requirements.
- Read sync path implemented for at least one resource.
- Declarative mappings exist for declared resources.
- Basic mapping/runtime validation passes.

#### Level 2 — Bidirectional production baseline

- Level 1 requirements.
- Read + write sync implemented for primary resources.
- Idempotency strategy defined and implemented.
- Conflict handling strategy defined and implemented.
- Conformance tests pass in SDK harness.

#### Level 3 — Operationally hardened

- Level 2 requirements.
- Webhook/event support (or explicit documented exception).
- Health metrics and sync lag visibility.
- Error-budget/SLO instrumentation and runbook references.

### Manifest metadata

Each connector manifest includes a `maturity` section:

- `level` (`0`–`3`)
- `tier` (`candidate`, `core`, `strategic`)
- `business_priority` (`1` highest)
- `capabilities` (`read`, `write`, `webhook`, `declarative_mapping`, `idempotent_write`, `conflict_handling`)
- `notes` (short rationale)
- `exceptions` (optional list of `{rule_id, expires_on, reason}` waivers for CI quality gates)

### Current priority cohort

Top-priority Level 2 cohort for this phase:

1. `jira`
2. `azure_devops`
3. `servicenow`
4. `salesforce`
5. `workday`
6. `sap`
7. `slack`
8. `teams`
9. `outlook`
10. `smartsheet`

---

## Microsoft 365 Field Mappings

This mapping aligns M365 workloads with required data types and identifies the preferred MCP tool key (when configured) or the Microsoft Graph REST endpoint to use.

### Legend

- **MCP tool key**: Key looked up in `tool_map` to resolve an MCP tool name.
- **Graph REST endpoint**: Microsoft Graph path used when MCP tooling is unavailable.

### Workload to data type mapping

| Workload | User list | Last activity | Subscription data | Cost data | Last login |
| --- | --- | --- | --- | --- | --- |
| Exchange/Outlook | MCP: `users.list` / REST: `/users` | MCP: `exchange.last_activity` / REST: `/reports/getEmailActivityUserDetail` | MCP: `subscriptions.list` / REST: `/subscribedSkus` | MCP: `billing.costs` / REST: `/reports/getOffice365ActivationCounts` | MCP: `signins.list` / REST: `/auditLogs/signIns` |
| Teams | MCP: `users.list` / REST: `/users` | MCP: `teams.last_activity` / REST: `/reports/getTeamsUserActivityUserDetail` | MCP: `subscriptions.list` / REST: `/subscribedSkus` | MCP: `billing.costs` / REST: `/reports/getOffice365ActivationCounts` | MCP: `signins.list` / REST: `/auditLogs/signIns` |
| SharePoint | MCP: `users.list` / REST: `/users` | MCP: `sharepoint.last_activity` / REST: `/reports/getSharePointActivityUserDetail` | MCP: `subscriptions.list` / REST: `/subscribedSkus` | MCP: `billing.costs` / REST: `/reports/getOffice365ActivationCounts` | MCP: `signins.list` / REST: `/auditLogs/signIns` |
| Planner | MCP: `users.list` / REST: `/users` | MCP: `planner.last_activity` / REST: `/reports/getOffice365ActiveUserDetail` | MCP: `subscriptions.list` / REST: `/subscribedSkus` | MCP: `billing.costs` / REST: `/reports/getOffice365ActivationCounts` | MCP: `signins.list` / REST: `/auditLogs/signIns` |
| OneDrive | MCP: `users.list` / REST: `/users` | MCP: `onedrive.last_activity` / REST: `/reports/getOneDriveActivityUserDetail` | MCP: `subscriptions.list` / REST: `/subscribedSkus` | MCP: `billing.costs` / REST: `/reports/getOffice365ActivationCounts` | MCP: `signins.list` / REST: `/auditLogs/signIns` |
| Power BI | MCP: `users.list` / REST: `/users` | MCP: `power_bi.last_activity` / REST: `/reports/getPowerBIActivityUserDetail` | MCP: `subscriptions.list` / REST: `/subscribedSkus` | MCP: `billing.costs` / REST: `/reports/getOffice365ActivationCounts` | MCP: `signins.list` / REST: `/auditLogs/signIns` |
| Viva | MCP: `users.list` / REST: `/users` | MCP: `viva.last_activity` / REST: `/reports/getOffice365ActiveUserDetail` | MCP: `subscriptions.list` / REST: `/subscribedSkus` | MCP: `billing.costs` / REST: `/reports/getOffice365ActivationCounts` | MCP: `signins.list` / REST: `/auditLogs/signIns` |

### Data table aggregation

The M365 connector supports requesting `data_table` for a workload, which expands into the five data types above (`user_list`, `last_activity`, `subscription_data`, `cost_data`, and `last_login`). The MCP tool key and Graph REST endpoint mappings for each data type are defined in `connectors/m365/tool_map.yaml`.

### File references

- YAML mapping file: `connectors/m365/tool_map.yaml`
- Connector manifest: `connectors/m365/manifest.yaml`

---

## IoT Connector Specification

**Purpose:** Specify the IoT connector's protocols, configuration schema, data normalisation model, and usage instructions.
**Audience:** Integration engineers, DevOps, and solution architects connecting IoT/OT telemetry to the platform.
**Owner:** Integration Engineering
**Last reviewed:** 2026-02-20

### Overview

The IoT connector ingests telemetry from custom hardware devices and normalizes sensor readings into the platform's canonical data model. It supports HTTP polling and MQTT streaming to accommodate different device communication patterns.

### Supported protocols

- **HTTP/HTTPS**: Poll device APIs for sensor data and device metadata.
- **MQTT**: Subscribe to topics for real-time sensor updates and publish command payloads.

### Configuration

Configure the connector using connector settings or environment variables.

#### Required settings (HTTP)

| Field | Description |
| --- | --- |
| `device_endpoint` | Base URL for the device API (e.g., `https://iot.example.com`). |
| `auth_token` | Bearer token used to authenticate HTTP requests. |
| `protocol` | Set to `http` or `https`. |

#### Required settings (MQTT)

| Field | Description |
| --- | --- |
| `mqtt_broker` | Hostname or IP of the MQTT broker. |
| `mqtt_port` | Port for the broker (default: 1883). |
| `protocol` | Set to `mqtt`. |

#### Optional settings

| Field | Description |
| --- | --- |
| `device_ids` | Comma-separated list of device IDs to filter polling. |
| `sensor_types` | Comma-separated list of sensor types to filter polling. |
| `mqtt_username` / `mqtt_password` | MQTT authentication credentials. |
| `mqtt_topic` | MQTT topic for subscribing/publishing (default: `devices/+/sensors`). |
| `poll_interval_seconds` | Polling interval for HTTP reads (default: 30 seconds). |

#### Environment variables

- `IOT_PROTOCOL`
- `IOT_DEVICE_ENDPOINT`
- `IOT_AUTH_TOKEN`
- `IOT_DEVICE_IDS`
- `IOT_SENSOR_TYPES`
- `IOT_MQTT_BROKER`
- `IOT_MQTT_PORT`
- `IOT_MQTT_USERNAME`
- `IOT_MQTT_PASSWORD`
- `IOT_MQTT_TOPIC`
- `IOT_POLL_INTERVAL_SECONDS`

### Data normalization

Incoming sensor payloads are normalized into the following fields:

| Field | Description |
| --- | --- |
| `device_id` | Device identifier for the sensor reading. |
| `sensor_type` | Type of sensor (e.g., temperature, vibration). |
| `value` | Sensor value or measurement. |
| `unit` | Measurement unit (e.g., °C, psi). |
| `observed_at` | Timestamp of the reading. |
| `metadata` | Any additional payload attributes. |

### Usage

1. Create a connector configuration and set the protocol-specific fields.
2. Test the connection using the API to validate device connectivity.
3. Enable the connector to begin polling or streaming data.

#### Example payload (HTTP)

```json
{
  "deviceId": "device-1",
  "sensorType": "temperature",
  "measurement": 72.5,
  "units": "F",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### Example normalized output

```json
{
  "source": "iot",
  "device_id": "device-1",
  "sensor_type": "temperature",
  "value": 72.5,
  "unit": "F",
  "observed_at": "2024-01-01T00:00:00Z",
  "metadata": {}
}
```

---

## MCP Server Configuration

### Purpose

Describe how to configure Model Context Protocol (MCP) servers for connector runtime routing, including authentication, scopes, tool mapping, and protocol initialization.

### Configuration surfaces

MCP server defaults live in the connector configuration layer and are surfaced to project-level connector configs.

- **Global connector defaults**: `ops/config/connectors/integrations.yaml` supports an `mcp` block (`server_id`, `server_url`, `client_id`, `client_secret`, `auth_scopes`, `tool_map`, `tools`) that defines defaults per connector and is referenced by the runtime configuration loader. Reference the config guide in `ops/config/README.md` for environment variable mappings and enablement flags.
- **Project-level overrides**: `ProjectConnectorConfigStore` persists per-project overrides in `data/connectors/project_config.json`, including MCP server URL, credentials, tool map, and routing flags.
- **Connector runtime fields**: the connector config model includes MCP-specific fields such as `mcp_server_url`, `mcp_server_id`, `protocol`, `protocol_version`, `mcp_client_id`, `mcp_client_secret`, `mcp_scope`, `mcp_api_key`, `mcp_api_key_header`, `mcp_oauth_token`, `tool_map`, `resource_map`, and routing controls like `prefer_mcp`, `mcp_enabled_operations`, and `mcp_disabled_operations`. These fields drive MCP routing and auth header construction at runtime.

### Authentication guidance

MCP servers can be protected with OAuth2, API keys, or pre-issued bearer tokens. Configure exactly one approach per connector instance.

#### OAuth client credentials

- Populate `mcp_client_id`, `mcp_client_secret`, and `mcp_scope` for MCP servers that require OAuth scopes.
- Set the MCP server URL via `mcp_server_url` (and `mcp_server_id` for logging and tracing).
- When using OAuth, ensure the server issues a bearer token that the MCP client can place in the `Authorization` header via `mcp_oauth_token`.

#### API key authentication

- Provide `mcp_api_key` and optionally override the header name with `mcp_api_key_header` (default `X-API-Key`).
- API keys are sent on every MCP JSON-RPC request, so scope them to the minimum tool set needed.

#### Bearer token authentication

- If your MCP gateway issues a static bearer token, set `mcp_oauth_token` and omit client credentials.
- Tokens are attached to the `Authorization: Bearer <token>` header on each request.

### Scopes and permissions

- Align `mcp_scope` with the tools your connector will call (for example, read-only scopes for sync-only connectors).
- Document any non-standard scopes in the connector manifest so operators know which permissions are required.

### Tool mapping

Tool mappings connect canonical connector operations to MCP tool names. MCP routing only works when the operation is mapped.

- Define tool mappings in the connector manifest under `mcp.tool_map` (for example, `list_invoices: sap.listInvoices`).
- Ensure the runtime configuration includes a `tool_map` entry; this is the authoritative mapping used by the MCP client when it calls `tools/call`.
- Validate the tool names by calling `tools/list` on the MCP server and confirming the tool names match the mapping keys.

### Protocol usage

MCP is a JSON-RPC protocol that exposes tools, resources, and prompts to AI applications. At runtime, the MCP client uses an initialization handshake and then performs discovery and invocation calls.

1. **Initialize**: call `initialize` with `protocolVersion` and client capabilities before any other request.
2. **Discover**: call `tools/list`, `resources/list`, and `agents/runtime/prompts/list` as needed.
3. **Invoke**: call `tools/call`, `resources/get`, `agents/runtime/prompts/get`, or `agents/runtime/prompts/call`.
4. **Notifications/tasks**: handle notifications (for example, `toolUpdate`) and optionally use `tasks/create` for long-running operations.

### Enablement checklist

1. Add the MCP server URL, credentials, scopes, and `protocol_version` to the environment (or secret store) referenced in `ops/config/README.md`.
2. Populate the connector's `mcp` block in `ops/config/connectors/integrations.yaml` and set `<CONNECTOR>_PREFER_MCP=true` when MCP should be preferred.
3. Populate `tool_map` (and optional `resource_map`/`prompt_map`) in the connector manifest and any project overrides so the router can resolve MCP primitives.
4. Confirm that MCP tools cover the required operations; if not, ensure REST connectors remain enabled as fallbacks.

### References

- [MCP specification](https://modelcontextprotocol.io/spec)
- [MCP architecture overview](https://modelcontextprotocol.io/architecture)

---

## MCP Connector Development

### Purpose

Provide a step-by-step guide for adding Model Context Protocol (MCP) connectors and extending MCP coverage across existing integrations.

### Prerequisites

- An MCP server that supports JSON-RPC `initialize`, `tools/list`, `tools/get`, and `tools/call` methods.
- A connector manifest that declares MCP protocol settings and tool mapping.
- REST connector coverage (optional but recommended) to serve as a fallback when MCP tools are missing or disabled.

### Add a new MCP connector

#### 1) Create the MCP connector package

1. Create a new connector folder under `connectors/<system>_mcp/`.
2. Add a `manifest.yaml` that declares `protocol: mcp`, includes MCP auth fields, and provides an `mcp.tool_map` section that maps canonical operations to MCP tool names. Use existing MCP manifests (for example, `connectors/sap_mcp/manifest.yaml`) as a template.
3. Add mappings under `connectors/<system>_mcp/mappings/` for any canonical entities you intend to sync.

#### 2) Register the connector

1. Add the MCP connector entry to `connectors/registry/connectors.json` with the correct `manifest_path` and metadata.
2. Update the supported systems documentation to include the MCP connector ID and coverage classification.

#### 3) Configure MCP defaults

1. Populate the connector's `mcp` block in `ops/config/connectors/integrations.yaml`, including `server_url`, `server_id`, `auth_scopes`, and `tool_map` defaults.
2. Add the MCP server URL and credentials to `.env` or your secret manager, following the environment variable mappings listed in `ops/config/README.md`.
3. Enable MCP preference with `<CONNECTOR>_PREFER_MCP=true` when MCP should be the default route.

#### 4) Verify tool mapping

1. Use the MCP server's `tools/list` response to confirm the tool names.
2. Ensure your `tool_map` in the manifest (and project-level overrides) uses exact tool names.
3. Confirm the connector's canonical operations map to the MCP client helper methods (`list_records`, `create_record`, `update_record`, `delete_record`) when appropriate.

#### 5) Optional resource and prompt mappings

- Add `resource_map` entries when the MCP server exposes read-only context resources (for example, project metadata or templates).
- Add `prompt_map` entries when the MCP server hosts reusable prompt templates for agents.

### Extend MCP coverage for an existing connector

1. Expand the `mcp.tool_map` in the MCP connector manifest for the missing operations.
2. Update `docs/connectors/mcp-coverage-matrix.md` to reflect new MCP tool coverage and remaining REST fallbacks.
3. If a REST fallback does not exist for a required operation, implement the REST mapping before enabling MCP preference to avoid sync gaps.

### Routing and fallback behavior

- MCP routing only happens when `prefer_mcp` is true, the MCP server URL is set, the operation is enabled, and a tool mapping exists for the operation.
- Missing tools or MCP client errors trigger an automatic fallback to REST so sync jobs can continue without MCP coverage.

### Troubleshooting

#### Auth errors (401/403)

- Verify the MCP server URL and credentials (`mcp_client_id`, `mcp_client_secret`, `mcp_oauth_token`, or `mcp_api_key`).
- Confirm the token or API key is injected into the request headers (bearer token in `Authorization` or API key header).
- Check that the configured scopes match the tool set your connector needs.

#### Missing tools or tool-map mismatches

- If the MCP client raises a "tool mapping missing" error, confirm `tool_map` includes the canonical operation key you are invoking.
- Validate the MCP server returns the expected tool name in `tools/list` and update the mapping to match exactly.

#### Fallback behavior

- If MCP calls fail, the operation router logs a warning and calls the REST connector instead. Ensure REST mappings exist for critical sync operations to avoid data gaps.
- Use `mcp_enabled_operations`/`mcp_disabled_operations` to narrow MCP usage for problematic operations while keeping MCP enabled for the rest.

---

## MCP Connector Onboarding

### Purpose

This guide provides internal onboarding steps, cross-system workflow examples, and troubleshooting tips for Model Context Protocol (MCP)-enabled connectors. It complements the [MCP Connector Development](#mcp-connector-development) and [MCP Server Configuration](#mcp-server-configuration) sections by focusing on day-to-day enablement, operational checks, and project-level configuration.

### When to use this guide

Use this guide when you need to:

- Enable MCP routing for an existing connector in a project.
- Validate MCP tool coverage for a new MCP server.
- Troubleshoot MCP routing and fallbacks in production or staging.

### Onboarding checklist

1. **Confirm MCP server readiness**
   - Verify the MCP server URL is reachable from the runtime environment.
   - Collect the MCP server ID used for tracing and log correlation.
   - Decide which authentication method applies (OAuth client credentials, API key, or bearer token).

2. **Validate tool inventory**
   - Call `tools/list` on the MCP server and capture the tool names.
   - Build a canonical operation → tool mapping for the connector (this becomes `tool_map`).
   - Confirm the tool names match the connector's expected operations before enabling MCP preference.

3. **Configure connector defaults**
   - Set MCP defaults in the connector configuration layer (env or `ops/config/connectors/integrations.yaml`).
   - Ensure `mcp_server_url`, `mcp_server_id`, and credentials are provided via secrets or environment variables.
   - Leave REST connector settings in place to preserve fallback behavior.

4. **Create project-level overrides (optional but recommended)**
   - Store project-specific MCP settings in `data/connectors/project_config.json` using `ProjectConnectorConfigStore`.
   - Override `tool_map`, `prefer_mcp`, or `mcp_enabled_operations` per project to control rollout scope.

5. **Enable MCP routing for the project**
   - Set `prefer_mcp=true` (or configure `mcp_enabled_operations`) when the tool map is complete.
   - Keep `mcp_disabled_operations` available for partial rollouts or targeted shutdowns.

6. **Validate runtime behavior**
   - Run a sync job in staging or a sandbox project.
   - Confirm MCP requests are emitted and that fallback behavior works when tools are missing.
   - Capture monitoring metrics for latency, errors, and fallback counts.

### Sample project configuration

A minimal, redacted example is provided in `examples/connector-configs/mcp-project-config.json`. It demonstrates:

- Multiple MCP connectors enabled for a single PPM project.
- Per-project MCP server URLs and tool mappings.
- Explicit `prefer_mcp` settings to opt-in for MCP routing.

### Cross-system workflow example

See `examples/workflows/mcp-cross-system.workflow.yaml` for a sample workflow that:

- Pulls work items from Jira via MCP.
- Creates or updates portfolio data in Planview.
- Notifies stakeholders in Slack using MCP tooling.

The accompanying Python script `examples/mcp_cross_system_demo.py` demonstrates the MCP client usage patterns (listing tools, invoking tools, and chaining results) and can be adapted into real integration jobs.

### Best practices

- **Use canonical operations and tool maps:** Ensure the operation router has a complete `tool_map` before enabling MCP preference.
- **Prefer gradual rollout:** Start with `mcp_enabled_operations` for low-risk reads, then expand to writes.
- **Keep REST fallbacks healthy:** Verify REST paths for critical operations so syncs continue if MCP tooling is unavailable.
- **Use least-privilege credentials:** Scope API keys and OAuth scopes to the minimum tool set required.
- **Document tool inventory:** Store `tools/list` output in the connector's internal notes so future updates can be validated quickly.
- **Capture telemetry:** Monitor MCP request rate, error rate, and fallback counts to evaluate tool coverage gaps.
- **Redact secrets in stored configs:** Project configs are stored in JSON; use the encryption key when possible and keep raw secrets in secret stores.

### Troubleshooting guide

| Symptom | Likely cause | Recommended fix |
| --- | --- | --- |
| `Tool mapping missing for <operation>` | `tool_map` missing or incomplete | Update the project config or connector defaults with the missing operation key. |
| HTTP 401 / auth errors | Missing or expired credentials | Verify `mcp_client_id`, `mcp_client_secret`, `mcp_oauth_token`, or API key values. |
| MCP calls falling back to REST | `prefer_mcp` disabled or missing tool map | Enable `prefer_mcp` and confirm tool names match `tools/list`. |
| MCP calls time out | Network or MCP server performance issues | Confirm connectivity and adjust MCP server scaling or client timeouts. |
| Partial MCP coverage | `mcp_enabled_operations` scoped too tightly | Expand allowed operations once tools are verified. |
| Empty `mcp_tools` list in UI | `tool_map` omitted in config | Populate `tool_map` so MCP tools are surfaced. |

---

## MCP Coverage Matrix

### Purpose

This matrix shows which SAP and Workday operations are currently backed by Model Context Protocol (MCP) tools versus REST connector coverage. It highlights gaps in MCP coverage, plus where REST read support exists and where write operations would need REST fallbacks.

### SAP

**Sources:**
- MCP tool map: `connectors/sap_mcp/manifest.yaml`
- REST connector mappings: `connectors/sap/manifest.yaml`

| Operation / entity | MCP tool (tool_map key → tool) | MCP read support | REST read support | Write support & fallback | Gaps / notes |
| --- | --- | --- | --- | --- | --- |
| Invoices | `list_invoices` → `sap.listInvoices` | ✅ | ❌ | ❌ No write tool; no REST write path | MCP read only; REST gap. |
| Goods receipts | `list_goods_receipts` → `sap.listGoodsReceipts` | ✅ | ❌ | ❌ No write tool; no REST write path | MCP read only; REST gap. |
| Purchase orders | `list_purchase_orders` → `sap.listPurchaseOrders` | ✅ | ✅ (`purchase_order` mapping) | ❌ No write tool; REST write not defined | REST can read via canonical sync; MCP has tool. |
| Suppliers | `list_suppliers` → `sap.listSuppliers` | ✅ | ❌ | ❌ No write tool; no REST write path | MCP read only; REST gap. |
| Projects (canonical sync) | — | ❌ | ✅ (`project` mapping) | ❌ No MCP write tool; REST write not defined | REST-only today; add MCP tool to close gap. |

### Workday

**Sources:**
- MCP tool map: `connectors/workday_mcp/manifest.yaml`
- REST connector mappings: `connectors/workday/manifest.yaml`

| Operation / entity | MCP tool (tool_map key → tool) | MCP read support | REST read support | Write support & fallback | Gaps / notes |
| --- | --- | --- | --- | --- | --- |
| Workers | `list_workers` → `workday.listWorkers` | ✅ | ❌ | ❌ No write tool; no REST write path | MCP read only; REST gap. |
| Job profiles | `list_job_profiles` → `workday.listJobProfiles` | ✅ | ❌ | ❌ No write tool; no REST write path | MCP read only; REST gap. |
| Positions | `list_positions` → `workday.listPositions` | ✅ | ❌ | ❌ No write tool; no REST write path | MCP read only; REST gap. |
| Organizations | `list_organizations` → `workday.listOrganizations` | ✅ | ❌ | ❌ No write tool; no REST write path | MCP read only; REST gap. |
| Projects (canonical sync) | — | ❌ | ✅ (`project` mapping) | ❌ No MCP write tool; REST write not defined | REST-only today; add MCP tool to close gap. |
| Resources (canonical sync) | — | ❌ | ✅ (`resource` mapping) | ❌ No MCP write tool; REST write not defined | REST-only today; add MCP tool to close gap. |

### Write-operation fallbacks

- MCP routing is operation-aware: if `prefer_mcp` is enabled and a tool is mapped, MCP is used; otherwise it falls back to REST. Missing MCP tools (or disabled MCP ops) route to REST automatically in `OperationRouter`.
- The MCP client expects CRUD-style mappings via `tool_map` (e.g., `create_record`, `update_record`), so write support requires explicit tool entries in the map.

### Extending MCP coverage

1. **Add or expand MCP tool mappings**
   - Update the MCP manifest `mcp.tool_map` for the connector (e.g., `connectors/sap_mcp/manifest.yaml`, `connectors/workday_mcp/manifest.yaml`).
   - If you're wiring MCP support into connector configs, populate `tool_map` in `ConnectorConfig` (this is the authoritative map the MCP client uses).

2. **Decide MCP vs REST routing**
   - Enable MCP routing using `prefer_mcp`, `mcp_enabled_operations`, or `mcp_disabled_operations` in the connector config and verify how `OperationRouter` resolves the operation.

3. **Add REST fallbacks for new write operations (if needed)**
   - If MCP tools for writes are not available, implement REST endpoints in the relevant connector or ensure the REST connector supports the write operation so the router can fall back safely.

---

## MCP Release Checklist

This checklist documents the validation points for MCP-enabled connectors, including registry and UI visibility, per-project configuration persistence, sync flow behavior, and operational readiness.

### Registry and UI visibility

- Confirm every MCP connector is listed in `connectors/registry/connectors.json`.
- Confirm the web UI loads connector metadata via `apps/web/src/main.py` using the registry path.
- Validate each MCP connector manifest path is present and resolves in the repo.

### MCP configuration persistence and per-project overrides

- Validate project-scoped connector configs persist to `data/connectors/project_config.json` (or the configured storage path).
- Ensure MCP tool maps are stored and round-tripped into `mcp_tools` for UI display.
- Confirm `enable_connector` disables other connectors within the same system or category to enforce per-project overrides.

### Sync flows (MCP, hybrid, and fallback)

- MCP-ready connectors should route through MCP when `prefer_mcp=true` and a tool map is present.
- Hybrid connectors should fall back to REST when MCP tools are missing or explicitly disabled.
- REST connectors should remain the default when MCP is not enabled.

### Docs, tests, CI, and monitoring

- Update connector inventory and MCP coverage documentation when MCP coverage changes.
- Add or update integration tests validating MCP routing and fallback behavior.
- Ensure CI pipelines run connector integration suites and coverage gates.
- Confirm monitoring dashboards cover MCP request rates, error rates, and fallback events.

### Release notes and deployment

- Capture MCP connector updates in `CHANGELOG.md` for the release tag.
- Follow the deployment runbook with environment-specific steps in `docs/runbooks/deployment.md`.

---

> The auto-generated connector capability matrix is maintained separately at [generated/capability-matrix.md](generated/capability-matrix.md).
