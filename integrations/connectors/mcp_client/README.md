# MCP Client Package

This package provides an async MCP (Model Context Protocol) client for invoking tools,
resources, prompts, and tasks via JSON-RPC.

## Configuration

### Required fields

When using `ConnectorConfig`, populate:

- `mcp_server_id`: The MCP server identifier.
- `mcp_server_url`: Base URL for JSON-RPC requests.
- `mcp_tool_map` (or `tool_map`): Tool mapping for high-level record methods.
- `protocol_version`: MCP protocol version used during initialization.

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

Define `mcp_tool_map` (or `tool_map`) to map record operations to tool names:

```json
{
  "list_records": "tools.listRecords",
  "create_record": "tools.createRecord",
  "update_record": "tools.updateRecord",
  "delete_record": "tools.deleteRecord"
}
```

The MCP client methods `list_records`, `create_record`, `update_record`, and `delete_record` will use this mapping.

### Initialization

The client performs an MCP `initialize` handshake before any other request (unless `auto_initialize=False`).
The handshake negotiates the protocol version and declares supported capabilities.

### Resources and prompts

The client exposes the MCP primitives for resources and prompts:

- `list_resources` / `get_resource`
- `list_prompts` / `get_prompt` / `call_prompt`

### Tasks and notifications

For experimental task support, use `create_task`, `get_task`, and `cancel_task`. Notifications can
be handled with `handle_notification` or by registering handlers via `register_notification_handler`.

### Tracing hooks

Pass a `trace_hook` callback (sync or async) and optional `trace_headers` to propagate trace context.
The hook receives `(event, payload)` where event is `request` or `response`.
