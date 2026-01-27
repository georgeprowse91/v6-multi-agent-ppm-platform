# Supported Systems

## Purpose

List connector coverage and maturity based on the current connector registry and configuration assets.

## Registry status

The authoritative list of connectors lives in `connectors/registry/connectors.json`.

| Connector ID | Name | Status | Certification |
| --- | --- | --- | --- |
| jira | Atlassian Jira Cloud | production | certified |
| planview | Planview | beta | automated |
| servicenow | ServiceNow | planned | not-started |
| sap | SAP S/4HANA | planned | not-started |

## Available connector scaffolding

Connector folders exist for additional systems with manifests, mappings, and tests but are not yet registered in the connector registry:

- Azure DevOps (`connectors/azure_devops`)
- Salesforce (`connectors/salesforce`)
- SharePoint (`connectors/sharepoint`)
- Slack (`connectors/slack`)
- Teams (`connectors/teams`)
- Workday (`connectors/workday`)

To enable these connectors, add registry entries and complete certification evidence per `docs/connectors/certification.md`.

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

- **Implemented:** Jira production connector with certification automation evidence; Planview connector in beta with OAuth2 runtime support.
- **Planned:** Add remaining connector registry entries and certification evidence.

## Related docs

- [Connector Overview](overview.md)
- [Connector Certification](certification.md)
- [Connector Data Mapping](data-mapping.md)
