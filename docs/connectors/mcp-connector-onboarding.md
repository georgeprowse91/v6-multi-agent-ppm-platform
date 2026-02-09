# MCP Connector Onboarding + Troubleshooting

## Purpose

This guide provides internal onboarding steps, cross-system workflow examples, and troubleshooting tips for Model Context Protocol (MCP)-enabled connectors. It complements the MCP development guide and MCP server configuration docs by focusing on day-to-day enablement, operational checks, and project-level configuration.

## When to use this guide

Use this guide when you need to:

- Enable MCP routing for an existing connector in a project.
- Validate MCP tool coverage for a new MCP server.
- Troubleshoot MCP routing and fallbacks in production or staging.

## Onboarding checklist

1. **Confirm MCP server readiness**
   - Verify the MCP server URL is reachable from the runtime environment.
   - Collect the MCP server ID used for tracing and log correlation.
   - Decide which authentication method applies (OAuth client credentials, API key, or bearer token).

2. **Validate tool inventory**
   - Call `tools/list` on the MCP server and capture the tool names.
   - Build a canonical operation → tool mapping for the connector (this becomes `tool_map`).
   - Confirm the tool names match the connector’s expected operations before enabling MCP preference.

3. **Configure connector defaults**
   - Set MCP defaults in the connector configuration layer (env or `config/connectors/integrations.yaml`).
   - Ensure `mcp_server_url`, `mcp_server_id`, and credentials are provided via secrets or environment variables.
   - Leave REST connector settings in place to preserve fallback behavior.

4. **Create project-level overrides (optional but recommended)**
   - Store project-specific MCP settings in `data/connectors/project_config.json` using `ProjectConnectorConfigStore`.
   - Override `tool_map`, `prefer_mcp`, or `mcp_enabled_operations` per project to control rollout scope.

5. **Enable MCP routing for the project**
   - Set `prefer_mcp=true` (or configure `mcp_enabled_operations`) when the tool map is complete.
   - Keep `mcp_disabled_operations` available for partial rollouts or targeted shutdowns.

6. **Validate runtime behavior**
   - Run a sync job in staging or a sandbox project.
   - Confirm MCP requests are emitted and that fallback behavior works when tools are missing.
   - Capture monitoring metrics for latency, errors, and fallback counts.

## Sample project configuration

A minimal, redacted example is provided in `examples/connector-configs/mcp-project-config.json`. It demonstrates:

- Multiple MCP connectors enabled for a single PPM project.
- Per-project MCP server URLs and tool mappings.
- Explicit `prefer_mcp` settings to opt-in for MCP routing.

## Cross-system workflow example

See `examples/workflows/mcp-cross-system.workflow.yaml` for a sample workflow that:

- Pulls work items from Jira via MCP.
- Creates or updates portfolio data in Planview.
- Notifies stakeholders in Slack using MCP tooling.

The accompanying Python script `examples/mcp_cross_system_demo.py` demonstrates the MCP client usage patterns (listing tools, invoking tools, and chaining results) and can be adapted into real integration jobs.

## Best practices

- **Use canonical operations and tool maps:** Ensure the operation router has a complete `tool_map` before enabling MCP preference.
- **Prefer gradual rollout:** Start with `mcp_enabled_operations` for low-risk reads, then expand to writes.
- **Keep REST fallbacks healthy:** Verify REST paths for critical operations so syncs continue if MCP tooling is unavailable.
- **Use least-privilege credentials:** Scope API keys and OAuth scopes to the minimum tool set required.
- **Document tool inventory:** Store `tools/list` output in the connector’s internal notes so future updates can be validated quickly.
- **Capture telemetry:** Monitor MCP request rate, error rate, and fallback counts to evaluate tool coverage gaps.
- **Redact secrets in stored configs:** Project configs are stored in JSON; use the encryption key when possible and keep raw secrets in secret stores.

## Troubleshooting guide

| Symptom | Likely cause | Recommended fix |
| --- | --- | --- |
| `Tool mapping missing for <operation>` | `tool_map` missing or incomplete | Update the project config or connector defaults with the missing operation key. |
| HTTP 401 / auth errors | Missing or expired credentials | Verify `mcp_client_id`, `mcp_client_secret`, `mcp_oauth_token`, or API key values. |
| MCP calls falling back to REST | `prefer_mcp` disabled or missing tool map | Enable `prefer_mcp` and confirm tool names match `tools/list`. |
| MCP calls time out | Network or MCP server performance issues | Confirm connectivity and adjust MCP server scaling or client timeouts. |
| Partial MCP coverage | `mcp_enabled_operations` scoped too tightly | Expand allowed operations once tools are verified. |
| Empty `mcp_tools` list in UI | `tool_map` omitted in config | Populate `tool_map` so MCP tools are surfaced. |

## Related documentation

- [MCP Server Configuration](mcp-server-configuration.md)
- [MCP Connector Development Guide](mcp-connector-development.md)
- [MCP Coverage Matrix](mcp-coverage-matrix.md)
