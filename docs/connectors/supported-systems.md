# Supported Systems

## Purpose

List connector coverage and maturity based on the current connector registry and packaged connector assets.

## Status definitions

- **production**: Certified connector with automated tests and runtime support.
- **beta**: Functional connector package with runtime support and in-progress certification.
- **preview**: Packaged connector (manifest + mappings + runner entrypoint) awaiting registry registration and certification evidence.

## Registry status (runtime-ready)

The authoritative registry list lives in `connectors/registry/connectors.json`.

| Connector ID | Name | Status | Certification |
| --- | --- | --- | --- |
| adp | ADP | beta | not-started |
| archer | RSA Archer | beta | not-started |
| asana | Asana | beta | not-started |
| azure_devops | Azure DevOps | beta | not-started |
| clarity | Clarity PPM | production | automated |
| confluence | Confluence | beta | not-started |
| google_drive | Google Drive | beta | not-started |
| jira | Atlassian Jira Cloud | production | certified |
| logicgate | LogicGate | beta | not-started |
| monday | Monday.com | beta | not-started |
| ms_project_server | Microsoft Project Server | beta | not-started |
| netsuite | NetSuite | beta | not-started |
| oracle | Oracle EPM | beta | not-started |
| planview | Planview | production | automated |
| salesforce | Salesforce | beta | not-started |
| sap | SAP S/4HANA | beta | not-started |
| sap_successfactors | SAP SuccessFactors | beta | not-started |
| servicenow | ServiceNow | beta | not-started |
| sharepoint | SharePoint | beta | not-started |
| slack | Slack | beta | not-started |
| teams | Microsoft Teams | beta | not-started |
| workday | Workday | beta | not-started |
| zoom | Zoom | beta | not-started |

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
