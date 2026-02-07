# MCP Connector Release Readiness Checklist

This checklist documents the validation points for MCP-enabled connectors, including registry + UI
visibility, per-project configuration persistence, sync flow behavior, and operational readiness.

## Registry + UI visibility

- Confirm every MCP connector is listed in `connectors/registry/connectors.json`.
- Confirm the web UI loads connector metadata via `apps/web/src/main.py` using the registry path.
- Validate each MCP connector manifest path is present and resolves in the repo.

## MCP configuration persistence + per-project overrides

- Validate project-scoped connector configs persist to `data/connectors/project_config.json` (or the
  configured storage path).
- Ensure MCP tool maps are stored and round-tripped into `mcp_tools` for UI display.
- Confirm `enable_connector` disables other connectors within the same system or category to enforce
  per-project overrides.

## Sync flows (MCP, hybrid, and fallback)

- MCP-ready connectors should route through MCP when `prefer_mcp=true` and a tool map is present.
- Hybrid connectors should fall back to REST when MCP tools are missing or explicitly disabled.
- REST connectors should remain the default when MCP is not enabled.

## Docs, tests, CI, and monitoring

- Update connector inventory and MCP coverage documentation when MCP coverage changes.
- Add or update integration tests validating MCP routing and fallback behavior.
- Ensure CI pipelines run connector integration suites and coverage gates.
- Confirm monitoring dashboards cover MCP request rates, error rates, and fallback events.

## Release notes + deployment

- Capture MCP connector updates in `CHANGELOG.md` for the release tag.
- Follow the deployment runbook with environment-specific steps in `docs/runbooks/deployment.md`.
