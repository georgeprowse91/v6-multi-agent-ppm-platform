# Supported Systems

## Purpose

List connector coverage and maturity based on the current connector registry and packaged connector assets.

## Status definitions

- **production**: Certified connector with automated tests and runtime support.
- **beta**: Functional connector package with runtime support and in-progress certification.

## Registry status (runtime-ready)

The authoritative registry list lives in `connectors/registry/connectors.json`.

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
  cat connectors/registry/connectors.json
  ```
- Check for connector manifests:
  ```bash
  rg -n "manifest.yaml" connectors/*/manifest.yaml
  ```

## Implementation status

- **Implemented:** Connector registry now includes every packaged connector.
- **Implemented:** All listed connector packages include manifests and runtime mappings.

## Related docs

- [Connector Overview](overview.md)
- [Connector Certification](certification.md)
- [Connector Data Mapping](data-mapping.md)
- [MCP Coverage Matrix](mcp-coverage-matrix.md)
