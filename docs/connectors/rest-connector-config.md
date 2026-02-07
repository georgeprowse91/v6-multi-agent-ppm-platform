# REST Connector Configuration

## Purpose

Document configuration expectations for REST-backed connectors, including project-level configuration and the fields each connector expects.

## Project-level configuration

REST connectors are configured per PPM project using `ProjectConnectorConfigStore`, which persists to `data/connectors/project_config.json`. Each stored configuration includes:

- `ppm_project_id` to scope the connector configuration to a single PPM project.
- Standard connector metadata (`connector_id`, `name`, `category`, sync settings).
- Connector-specific non-secret fields (for example, `instance_url`, `project_key`).
- Secret values sourced from environment variables or secret managers, as listed below.

## OAuth rotation fields

OAuth 2.0 connectors support additional optional fields:

- `rotation_enabled`
- `rotation_provider`
- `refresh_token_rotation_days`
- `client_secret_rotation_days`

## REST connector configuration matrix

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

## MCP monitoring

When a vendor or marketplace announces an MCP server for a REST connector, update the connector classification to add an MCP entry in the registry, mark `mcp_preferred` when appropriate, and keep the REST connector available as a fallback for project-level configurations.
