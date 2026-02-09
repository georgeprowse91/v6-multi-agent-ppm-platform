# MCP Connector Development Guide

## Purpose

Provide a step-by-step guide for adding Model Context Protocol (MCP) connectors and extending MCP coverage across existing integrations.

## Prerequisites

- An MCP server that supports JSON-RPC `initialize`, `tools/list`, `tools/get`, and `tools/call` methods.
- A connector manifest that declares MCP protocol settings and tool mapping.
- REST connector coverage (optional but recommended) to serve as a fallback when MCP tools are missing or disabled.

## Add a new MCP connector

### 1) Create the MCP connector package

1. Create a new connector folder under `integrations/connectors/<system>_mcp/`.
2. Add a `manifest.yaml` that declares `protocol: mcp`, includes MCP auth fields, and provides an `mcp.tool_map` section that maps canonical operations to MCP tool names. Use existing MCP manifests (for example, `integrations/connectors/sap_mcp/manifest.yaml`) as a template.
3. Add mappings under `integrations/connectors/<system>_mcp/mappings/` for any canonical entities you intend to sync.

### 2) Register the connector

1. Add the MCP connector entry to `integrations/connectors/registry/connectors.json` with the correct `manifest_path` and metadata.
2. Update the supported systems documentation to include the MCP connector ID and coverage classification.

### 3) Configure MCP defaults

1. Populate the connector’s `mcp` block in `config/connectors/integrations.yaml`, including `server_url`, `server_id`, `auth_scopes`, and `tool_map` defaults.
2. Add the MCP server URL and credentials to `.env` or your secret manager, following the environment variable mappings listed in `config/README.md`.
3. Enable MCP preference with `<CONNECTOR>_PREFER_MCP=true` when MCP should be the default route.

### 4) Verify tool mapping

1. Use the MCP server’s `tools/list` response to confirm the tool names.
2. Ensure your `tool_map` in the manifest (and project-level overrides) uses exact tool names.
3. Confirm the connector’s canonical operations map to the MCP client helper methods (`list_records`, `create_record`, `update_record`, `delete_record`) when appropriate.

### 5) Optional resource and prompt mappings

- Add `resource_map` entries when the MCP server exposes read-only context resources (for example, project metadata or templates).
- Add `prompt_map` entries when the MCP server hosts reusable prompt templates for agents.

## Extend MCP coverage for an existing connector

1. Expand the `mcp.tool_map` in the MCP connector manifest for the missing operations.
2. Update `docs/connectors/mcp-coverage.md` and `docs/connectors/mcp-coverage-matrix.md` to reflect new MCP tool coverage and remaining REST fallbacks.
3. If a REST fallback does not exist for a required operation, implement the REST mapping before enabling MCP preference to avoid sync gaps.

## Routing and fallback behavior

- MCP routing only happens when `prefer_mcp` is true, the MCP server URL is set, the operation is enabled, and a tool mapping exists for the operation.
- Missing tools or MCP client errors trigger an automatic fallback to REST so sync jobs can continue without MCP coverage.

## Troubleshooting

### Auth errors (401/403)

- Verify the MCP server URL and credentials (`mcp_client_id`, `mcp_client_secret`, `mcp_oauth_token`, or `mcp_api_key`).
- Confirm the token or API key is injected into the request headers (bearer token in `Authorization` or API key header).
- Check that the configured scopes match the tool set your connector needs.

### Missing tools or tool-map mismatches

- If the MCP client raises a “tool mapping missing” error, confirm `tool_map` includes the canonical operation key you are invoking.
- Validate the MCP server returns the expected tool name in `tools/list` and update the mapping to match exactly.

### Fallback behavior

- If MCP calls fail, the operation router logs a warning and calls the REST connector instead. Ensure REST mappings exist for critical sync operations to avoid data gaps.
- Use `mcp_enabled_operations`/`mcp_disabled_operations` to narrow MCP usage for problematic operations while keeping MCP enabled for the rest.
