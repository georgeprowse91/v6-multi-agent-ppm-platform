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
| jira | Atlassian Jira Cloud | production | certified |
| planview | Planview | production | automated |
| clarity | Clarity PPM | production | automated |
| servicenow | ServiceNow | beta | not-started |
| sap | SAP S/4HANA | beta | not-started |

## Packaged connectors (manifested, ready for registration)

These connectors include manifests, mappings, and runtime entrypoints but are not yet registered in the registry:

| Connector ID | Name | Status |
| --- | --- | --- |
| azure_devops | Azure DevOps | preview |
| salesforce | Salesforce | preview |
| sharepoint | SharePoint | preview |
| slack | Slack | preview |
| teams | Microsoft Teams | preview |
| workday | Workday | preview |

## Scaffolded directories (structure only)

Connector directories exist without manifests for future additions:

- adp
- archer
- asana
- confluence
- google_drive
- logicgate
- monday
- ms_project_server
- netsuite
- oracle
- sap_successfactors
- zoom

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

- **Implemented:** Jira, Planview, Clarity connectors in the registry with runtime packages.
- **Implemented:** ServiceNow and SAP connector packages with registry entries and manifest-backed runtime configuration.
- **In progress:** Register and certify the remaining packaged connectors.

## Related docs

- [Connector Overview](overview.md)
- [Connector Certification](certification.md)
- [Connector Data Mapping](data-mapping.md)
