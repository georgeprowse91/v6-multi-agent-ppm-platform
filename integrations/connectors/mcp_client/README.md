# MCP Client Package

This package provides an async MCP (Model Context Protocol) client for invoking tools via JSON-RPC.

## Configuration

### Required fields

When using `ConnectorConfig`, populate:

- `mcp_server_id`: The MCP server identifier.
- `mcp_server_url`: Base URL for JSON-RPC requests.
- `mcp_tool_map`: Tool mapping for high-level record methods.

### Optional overrides

- `override_url`: A per-request override for the MCP base URL.

### Authentication

Authentication values can come from either `ConnectorConfig.custom_fields` or environment variables.
If both are provided, connector config values are preferred, then env values are used as fallback.

`ConnectorConfig.custom_fields` keys:

- `mcp_api_key`
- `mcp_api_key_header` (defaults to `X-API-Key`)
- `mcp_oauth_token`
- `mcp_client_id`
- `mcp_client_secret`
- `mcp_scope`

Environment variables:

- `MCP_API_KEY`
- `MCP_API_KEY_HEADER` (defaults to `X-API-Key`)
- `MCP_OAUTH_TOKEN`
- `MCP_CLIENT_ID`
- `MCP_CLIENT_SECRET`
- `MCP_SCOPE`

### Tool map for record operations

Define `mcp_tool_map` to map record operations to tool names:

```json
{
  "list_records": "tools.listRecords",
  "create_record": "tools.createRecord",
  "update_record": "tools.updateRecord",
  "delete_record": "tools.deleteRecord"
}
```

The MCP client methods `list_records`, `create_record`, `update_record`, and `delete_record` will use this mapping.

### Tracing hooks

Pass a `trace_hook` callback (sync or async) and optional `trace_headers` to propagate trace context.
The hook receives `(event, payload)` where event is `request` or `response`.
