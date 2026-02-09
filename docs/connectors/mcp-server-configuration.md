# MCP Server Configuration

## Purpose

Describe how to configure Model Context Protocol (MCP) servers for connector runtime routing, including authentication, scopes, tool mapping, and protocol initialization.

## Configuration surfaces

MCP server defaults live in the connector configuration layer and are surfaced to project-level connector configs.

- **Global connector defaults**: `config/connectors/integrations.yaml` supports an `mcp` block (`server_id`, `server_url`, `client_id`, `client_secret`, `auth_scopes`, `tool_map`, `tools`) that defines defaults per connector and is referenced by the runtime configuration loader. Reference the config guide in `config/README.md` for environment variable mappings and enablement flags.
- **Project-level overrides**: `ProjectConnectorConfigStore` persists per-project overrides in `data/connectors/project_config.json`, including MCP server URL, credentials, tool map, and routing flags.
- **Connector runtime fields**: the connector config model includes MCP-specific fields such as `mcp_server_url`, `mcp_server_id`, `protocol`, `protocol_version`, `mcp_client_id`, `mcp_client_secret`, `mcp_scope`, `mcp_api_key`, `mcp_api_key_header`, `mcp_oauth_token`, `tool_map`, `resource_map`, and routing controls like `prefer_mcp`, `mcp_enabled_operations`, and `mcp_disabled_operations`. These fields drive MCP routing and auth header construction at runtime.

## Authentication guidance

MCP servers can be protected with OAuth2, API keys, or pre-issued bearer tokens. Configure exactly one approach per connector instance.

### OAuth client credentials

- Populate `mcp_client_id`, `mcp_client_secret`, and `mcp_scope` for MCP servers that require OAuth scopes.
- Set the MCP server URL via `mcp_server_url` (and `mcp_server_id` for logging and tracing).
- When using OAuth, ensure the server issues a bearer token that the MCP client can place in the `Authorization` header via `mcp_oauth_token`.

### API key authentication

- Provide `mcp_api_key` and optionally override the header name with `mcp_api_key_header` (default `X-API-Key`).
- API keys are sent on every MCP JSON-RPC request, so scope them to the minimum tool set needed.

### Bearer token authentication

- If your MCP gateway issues a static bearer token, set `mcp_oauth_token` and omit client credentials.
- Tokens are attached to the `Authorization: Bearer <token>` header on each request.

## Scopes and permissions

- Align `mcp_scope` with the tools your connector will call (for example, read-only scopes for sync-only connectors).
- Document any non-standard scopes in the connector manifest so operators know which permissions are required.

## Tool mapping

Tool mappings connect canonical connector operations to MCP tool names. MCP routing only works when the operation is mapped.

- Define tool mappings in the connector manifest under `mcp.tool_map` (for example, `list_invoices: sap.listInvoices`).
- Ensure the runtime configuration includes a `tool_map` entry; this is the authoritative mapping used by the MCP client when it calls `tools/call`.
- Validate the tool names by calling `tools/list` on the MCP server and confirming the tool names match the mapping keys.

## Protocol usage

MCP is a JSON-RPC protocol that exposes tools, resources, and prompts to AI applications.
At runtime, the MCP client uses an initialization handshake and then performs discovery and invocation calls.

1. **Initialize**: call `initialize` with `protocolVersion` and client capabilities before any other request.
2. **Discover**: call `tools/list`, `resources/list`, and `prompts/list` as needed.
3. **Invoke**: call `tools/call`, `resources/get`, `prompts/get`, or `prompts/call`.
4. **Notifications/tasks**: handle notifications (for example, `toolUpdate`) and optionally use `tasks/create` for long-running operations.

## Enablement checklist

1. Add the MCP server URL, credentials, scopes, and `protocol_version` to the environment (or secret store) referenced in `config/README.md`.
2. Populate the connector’s `mcp` block in `config/connectors/integrations.yaml` and set `<CONNECTOR>_PREFER_MCP=true` when MCP should be preferred.
3. Populate `tool_map` (and optional `resource_map`/`prompt_map`) in the connector manifest and any project overrides so the router can resolve MCP primitives.
4. Confirm that MCP tools cover the required operations; if not, ensure REST connectors remain enabled as fallbacks.

## References

- MCP specification: https://modelcontextprotocol.io/spec
- MCP architecture overview: https://modelcontextprotocol.io/architecture
