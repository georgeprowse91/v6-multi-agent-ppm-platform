# Generated Connector Capability Matrix

This table is generated from connector manifests plus the maturity inventory output.
Do not edit by hand; run `python ops/tools/codegen/generate_docs.py`.

| Connector | Name | Maturity level | Auth | Sync modes | Read | Write | Webhook | Mapping completeness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `adp` | Adp | 0 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `archer` | Archer | 0 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `asana` | Asana | 0 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `confluence` | Confluence | 0 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `google_drive` | Google Drive | 0 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `jira` | Jira | 2 | `api_key` | bi-directional | ✅ | ✅ | ✅ | 1.00 |
| `logicgate` | Logicgate | 0 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `monday` | Monday | 0 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `ms_project_server` | Ms Project Server | 0 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `netsuite` | Netsuite | 0 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `oracle` | Oracle | 0 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `sap_successfactors` | Sap Successfactors | 0 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `zoom` | Zoom | 0 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `azure_devops` | Azure DevOps | 2 | `token` | full, incremental | ✅ | ✅ | ✅ | 1.00 |
| `servicenow` | ServiceNow | 2 | `oauth2` | full, incremental | ✅ | ✅ | ✅ | 1.00 |
| `salesforce` | Salesforce | 2 | `oauth2` | full, incremental | ✅ | ✅ | ✅ | 1.00 |
| `workday` | Workday | 2 | `oauth2` | full, incremental | ✅ | ✅ | ❌ | 1.00 |
| `sap` | SAP | 2 | `basic` | full, incremental | ✅ | ✅ | ❌ | 1.00 |
| `slack` | Slack | 2 | `api_key` | full, incremental | ✅ | ✅ | ✅ | 1.00 |
| `teams` | Microsoft Teams | 2 | `oauth2` | full, incremental | ✅ | ✅ | ✅ | 1.00 |
| `outlook` | Outlook | 2 | `oauth2` | full, incremental | ✅ | ✅ | ✅ | 1.00 |
| `smartsheet` | Smartsheet | 2 | `api_token` | full, incremental | ✅ | ✅ | ❌ | 1.00 |
| `azure_communication_services` | Azure Communication Services | 1 | `api_key` | incremental | ✅ | ❌ | ❌ | 1.00 |
| `clarity` | Clarity PPM | 1 | `oauth2` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `clarity_mcp` | Clarity PPM (MCP) | 1 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `google_calendar` | Google Calendar | 1 | `oauth2` | full, incremental | ✅ | ❌ | ✅ | 1.00 |
| `iot` | IoT Integrations | 1 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `jira_mcp` | Jira (MCP) | 1 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `m365` | Microsoft 365 | 1 | `oauth2` | full, incremental | ✅ | ❌ | ✅ | 1.00 |
| `notification_hubs` | Azure Notification Hubs | 1 | `sas` | incremental | ✅ | ❌ | ❌ | 1.00 |
| `planview` | Planview | 1 | `oauth2` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `planview_mcp` | Planview (MCP) | 1 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `sap_mcp` | SAP (MCP) | 1 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `sharepoint` | SharePoint | 1 | `oauth2` | full, incremental | ✅ | ❌ | ✅ | 1.00 |
| `slack_mcp` | Slack (MCP) | 1 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `teams_mcp` | Microsoft Teams (MCP) | 1 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |
| `twilio` | Twilio | 1 | `basic` | incremental | ✅ | ❌ | ✅ | 1.00 |
| `workday_mcp` | Workday (MCP) | 1 | `api_key` | full, incremental | ✅ | ❌ | ❌ | 1.00 |

## Inventory summary

- Total connectors: **38**
- Read enabled: **38**
- Write enabled: **10**
- Webhook enabled: **11**
