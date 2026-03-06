# Credential Acquisition Guide

Guide for acquiring and configuring credentials used by the PPM platform.

## Azure Credentials

### Service Principal

1. Create a service principal for the platform:
   ```bash
   az ad sp create-for-rbac --name ppm-platform-sp --role contributor
   ```
2. Store the output credentials securely in Key Vault.
3. Configure workload identity federation for Kubernetes pods.

### Azure OpenAI

1. Provision an Azure OpenAI resource in the target subscription.
2. Deploy required models (GPT-4o, text-embedding-ada-002).
3. Copy the API key and endpoint to Key Vault.

## Connector Credentials

Each external connector requires its own set of credentials:

| Connector | Credential Type | Acquisition |
|-----------|----------------|-------------|
| Jira | API Token | Atlassian account settings |
| Azure DevOps | PAT | Azure DevOps user settings |
| Slack | Bot Token | Slack app configuration |
| Teams | App Registration | Azure AD app registrations |
| ServiceNow | OAuth Client | ServiceNow admin console |
| SAP | Technical User | SAP Basis administration |

### Steps

1. Obtain credentials from the respective system administrator.
2. Store credentials in Azure Key Vault under the connector prefix.
3. Configure the connector manifest in `connectors/registry/connectors.json`.
4. Validate connectivity using `make test-connector-smoke`.

## Security Requirements

- Never store credentials in source code or configuration files.
- All credentials must be rotated according to the organization's security policy.
- Use managed identities where possible to avoid static credentials.
