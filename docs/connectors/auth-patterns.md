# Connector Authentication Patterns

## Purpose

Document the authentication patterns supported by connector manifests and configuration files.

## Configuration sources

- Connector manifests (`integrations/connectors/<name>/manifest.yaml`) specify the auth type expected by the connector.
- Environment-specific configuration is stored in `ops/config/connectors/integrations.yaml` and references secrets via environment variables.
- Auth schema guidance lives in `integrations/connectors/registry/schemas/auth-config.schema.json`.

## Supported patterns

| Auth type | Description | Example connector |
| --- | --- | --- |
| `oauth2` | OAuth 2.0 client credentials or auth code flows | SAP, Workday |
| `api_token` | Static API token with optional email/user | Jira |
| `pat` | Personal access token | Azure DevOps |
| `bot_token` | Bot tokens for chat integrations | Slack |
| `app_credentials` | App registration credentials (client id/secret) | Teams |
| `azure_ad` | Azure AD-based integration | SharePoint |

## MCP connector authentication

MCP-enabled connectors can delegate authentication to an MCP server. Configure the MCP server URL and ID in `.env` (for example, `SLACK_MCP_SERVER_URL`, `TEAMS_MCP_SERVER_URL`) and supply MCP OAuth client credentials when the MCP server expects OAuth (`*_MCP_CLIENT_ID`, `*_MCP_CLIENT_SECRET`). Set `<CONNECTOR>_PREFER_MCP=true` to route connector traffic through MCP for the matching connector ID.

## Storing MCP OAuth secrets in managed secret stores

Use managed secret stores in production and map secret values to the environment variables expected by MCP connectors. Local development can rely on a `.env` file (kept out of source control). See [ADR 0010](../architecture/adr/0010-secrets-management.md) for the production practices and local development split.

### Azure Key Vault

- Create Key Vault secrets that match the env var names, or define explicit mappings if you need different naming.
- Use SecretProviderClass or your runtime injector to expose the secrets as environment variables.

Example mapping (Key Vault secret → env var):

| Key Vault secret name | Runtime env var |
| --- | --- |
| `PLANVIEW_MCP_CLIENT_ID` | `PLANVIEW_MCP_CLIENT_ID` |
| `PLANVIEW_MCP_CLIENT_SECRET` | `PLANVIEW_MCP_CLIENT_SECRET` |
| `PLANVIEW_MCP_SERVER_URL` | `PLANVIEW_MCP_SERVER_URL` |

### AWS Secrets Manager

- Store secrets as discrete entries or a single JSON secret.
- Configure your runtime to map keys to env vars (ECS task definition, Kubernetes External Secrets, etc.).

Example mapping (JSON secret `mcp/planview` → env var):

| Secrets Manager key | Runtime env var |
| --- | --- |
| `PLANVIEW_MCP_CLIENT_ID` | `PLANVIEW_MCP_CLIENT_ID` |
| `PLANVIEW_MCP_CLIENT_SECRET` | `PLANVIEW_MCP_CLIENT_SECRET` |
| `PLANVIEW_MCP_SERVER_URL` | `PLANVIEW_MCP_SERVER_URL` |

## Operational guidance

1. Store secrets in your secret manager and inject via env vars.
2. Update `ops/config/connectors/integrations.yaml` with the secret references.
3. Ensure manifests and mappings are registered in `integrations/connectors/registry/connectors.json` before enabling the connector.

## Verification steps

- Inspect the integration configuration:
  ```bash
  sed -n '1,200p' ops/config/connectors/integrations.yaml
  ```
- Validate connector manifest auth sections:
  ```bash
  rg -n "auth:" integrations/connectors/*/manifest.yaml
  ```

## Implementation status

- **Implemented:** Manifest auth definitions, environment configuration structure.
- **Implemented:** OAuth refresh token management with optional Key Vault rotation support.

## Related docs

- [Connector Overview](overview.md)
- [Connector Certification](certification.md)
- [Security Architecture](../architecture/security-architecture.md)
