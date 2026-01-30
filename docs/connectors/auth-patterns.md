# Connector Authentication Patterns

## Purpose

Document the authentication patterns supported by connector manifests and configuration files.

## Configuration sources

- Connector manifests (`connectors/<name>/manifest.yaml`) specify the auth type expected by the connector.
- Environment-specific configuration is stored in `config/connectors/integrations.yaml` and references secrets via environment variables.
- Auth schema guidance lives in `connectors/registry/schemas/auth-config.schema.json`.

## Supported patterns

| Auth type | Description | Example connector |
| --- | --- | --- |
| `oauth2` | OAuth 2.0 client credentials or auth code flows | SAP, Workday |
| `api_token` | Static API token with optional email/user | Jira |
| `pat` | Personal access token | Azure DevOps |
| `bot_token` | Bot tokens for chat integrations | Slack |
| `app_credentials` | App registration credentials (client id/secret) | Teams |
| `azure_ad` | Azure AD-based integration | SharePoint |

## Operational guidance

1. Store secrets in your secret manager and inject via env vars.
2. Update `config/connectors/integrations.yaml` with the secret references.
3. Ensure manifests and mappings are registered in `connectors/registry/connectors.json` before enabling the connector.

## Verification steps

- Inspect the integration configuration:
  ```bash
  sed -n '1,200p' config/connectors/integrations.yaml
  ```
- Validate connector manifest auth sections:
  ```bash
  rg -n "auth:" connectors/*/manifest.yaml
  ```

## Implementation status

- **Implemented:** Manifest auth definitions, environment configuration structure.
- **Implemented:** OAuth refresh token management with optional Key Vault rotation support.

## Related docs

- [Connector Overview](overview.md)
- [Connector Certification](certification.md)
- [Security Architecture](../architecture/security-architecture.md)
