# Supported Systems

## Purpose

List connector coverage and maturity based on the current connector registry and packaged connector assets.

## Status definitions

- **production**: Certified connector with automated tests and runtime support.
- **beta**: Functional connector package with runtime support and in-progress certification.

## MCP vs REST support summary

This table summarizes whether a system is covered by REST-only connectors, MCP-only tooling, or a hybrid of the two. Use the MCP coverage docs for operation-level details.

| System | REST connector ID | MCP connector ID | Coverage | Notes |
| --- | --- | --- | --- | --- |
| ADP | `adp` | — | REST-only | REST connectors cover worker/payroll reads. |
| Archer (RSA Archer) | `archer` | — | REST-only | REST reads for risk/GRC entities. |
| Asana | `asana` | — | REST-only | REST reads/writes for projects and tasks. |
| Azure Communication Services | `azure_communication_services` | — | REST-only | REST reads/writes for SMS/email. |
| Azure DevOps | `azure_devops` | — | REST-only | REST reads/writes for projects and work items. |
| Clarity PPM | `clarity` | — | REST-only | REST reads for projects. |
| Confluence | `confluence` | — | REST-only | REST reads/writes for spaces and pages. |
| Google Calendar | `google_calendar` | — | REST-only | REST reads/writes for calendar events. |
| Google Drive | `google_drive` | — | REST-only | REST reads/writes for files and folders. |
| IoT Integrations | `iot` | — | REST-only | REST reads/writes for devices and sensor data. |
| Jira | `jira` | `jira_mcp` | MCP-ready | MCP tools cover project/issue reads and issue writes. |
| LogicGate | `logicgate` | — | REST-only | REST reads/writes for workflows and records. |
| Monday.com | `monday` | — | REST-only | REST reads/writes for boards and items. |
| Microsoft Project Server | `ms_project_server` | — | REST-only | REST reads/writes for projects and tasks. |
| NetSuite | `netsuite` | — | REST-only | REST reads for projects/customers. |
| Azure Notification Hubs | `notification_hubs` | — | REST-only | REST reads/writes for notifications. |
| Oracle ERP Cloud | `oracle` | — | REST-only | REST reads for projects and invoices. |
| Outlook | `outlook` | — | REST-only | REST reads/writes for calendar data. |
| Planview | `planview` | — | REST-only | REST reads for projects. |
| Salesforce | `salesforce` | — | REST-only | REST reads for projects. |
| SAP | `sap` | `sap_mcp` | Hybrid | MCP reads for finance/procurement; REST reads for project sync. |
| SAP SuccessFactors | `sap_successfactors` | — | REST-only | REST reads for users and jobs. |
| ServiceNow GRC | `servicenow` | — | REST-only | REST reads/writes for profiles and risks. |
| SharePoint | `sharepoint` | — | REST-only | REST reads/writes for documents and lists. |
| Slack | `slack` | `slack_mcp` | MCP-ready | MCP tools cover channels/users reads and message writes. |
| Smartsheet | `smartsheet` | — | REST-only | REST reads/writes for sheets and workspaces. |
| Microsoft Teams | `teams` | `teams_mcp` | Hybrid | MCP reads for teams/channels and message writes; REST reads for messages. |
| Twilio | `twilio` | — | REST-only | REST reads/writes for messages. |
| Workday | `workday` | `workday_mcp` | MCP-ready | MCP tools cover worker/position reads; REST handles canonical project/resource sync. |
| Zoom | `zoom` | — | REST-only | REST reads for meetings/webinars. |

## Registry status (runtime-ready)

The authoritative registry list lives in `integrations/connectors/registry/connectors.json`.

| Connector ID | Name | Category | Sync Directions | Status | Certification |
| --- | --- | --- | --- | --- | --- |
| adp | ADP | hris | inbound | beta | not-started |
| archer | RSA Archer | grc | inbound | beta | not-started |
| asana | Asana | pm | inbound, bidirectional | beta | not-started |
| azure_devops | Azure DevOps | pm | inbound, bidirectional | beta | not-started |
| azure_communication_services | Azure Communication Services | collaboration | outbound | beta | not-started |
| clarity | Clarity PPM | ppm | inbound, bidirectional | production | automated |
| confluence | Confluence | doc_mgmt | inbound | beta | not-started |
| google_drive | Google Drive | doc_mgmt | inbound, bidirectional | beta | not-started |
| google_calendar | Google Calendar | collaboration | inbound, bidirectional | beta | not-started |
| iot | IoT Integrations | iot | inbound, outbound | production | not-started |
| jira | Jira | pm | inbound | production | certified |
| jira_mcp | Jira (MCP) | pm | inbound | beta | not-started |
| logicgate | LogicGate | grc | inbound, bidirectional | beta | not-started |
| monday | Monday.com | pm | inbound, bidirectional | beta | not-started |
| ms_project_server | Microsoft Project Server | ppm | inbound, bidirectional | beta | not-started |
| netsuite | NetSuite | erp | inbound | beta | not-started |
| notification_hubs | Azure Notification Hubs | collaboration | outbound | beta | not-started |
| oracle | Oracle ERP Cloud | erp | inbound | beta | not-started |
| outlook | Outlook | collaboration | inbound, bidirectional | beta | not-started |
| planview | Planview | ppm | inbound, bidirectional | production | automated |
| salesforce | Salesforce | crm | inbound | beta | not-started |
| sap | SAP | erp | inbound | beta | not-started |
| sap_mcp | SAP (MCP) | erp | inbound | beta | not-started |
| sap_successfactors | SAP SuccessFactors | hris | inbound | beta | not-started |
| servicenow | ServiceNow GRC | grc | inbound, bidirectional | beta | not-started |
| sharepoint | SharePoint | doc_mgmt | inbound, bidirectional | beta | not-started |
| slack | Slack | collaboration | inbound, outbound, bidirectional | beta | not-started |
| slack_mcp | Slack (MCP) | collaboration | inbound, outbound, bidirectional | beta | not-started |
| smartsheet | Smartsheet | pm | inbound, bidirectional | beta | not-started |
| teams | Microsoft Teams | collaboration | outbound, bidirectional | beta | not-started |
| teams_mcp | Microsoft Teams (MCP) | collaboration | outbound, bidirectional | beta | not-started |
| twilio | Twilio | collaboration | outbound, bidirectional | beta | not-started |
| workday | Workday | hris | inbound | beta | not-started |
| workday_mcp | Workday (MCP) | hris | inbound | beta | not-started |
| zoom | Zoom | collaboration | inbound, outbound | beta | not-started |

## Verification steps

- View the registry:
  ```bash
  cat integrations/connectors/registry/connectors.json
  ```
- Check for connector manifests:
  ```bash
  rg -n "manifest.yaml" integrations/connectors/*/manifest.yaml
  ```

## Implementation status

- **Implemented:** Connector registry now includes every packaged connector.
- **Implemented:** All listed connector packages include manifests and runtime mappings.

## Related docs

- [Connector Overview](overview.md)
- [Connector Certification](certification.md)
- [Connector Data Mapping](data-mapping.md)
- [MCP Coverage Classification](mcp-coverage.md)
- [MCP Coverage Matrix](mcp-coverage-matrix.md)
