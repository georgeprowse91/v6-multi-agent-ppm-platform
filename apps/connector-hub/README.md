# Connector Hub

Registry and sandbox assets for external connectors (Jira, SAP, etc.) in the PPM platform.

## Current state

- Connector manifests and metadata live under `apps/connector-hub/registry/`.
- Sandbox rules are validated via `scripts/validate-connector-sandbox.py`.
- No standalone service is wired yet; the hub is a source-of-truth registry.

## Quickstart

Validate the connector sandbox rules:

```bash
python scripts/validate-connector-sandbox.py
```

## How to verify

```bash
ls apps/connector-hub/registry
```

Expected output includes connector manifests and registry metadata.

## Key files

- `apps/connector-hub/registry/`: connector manifests and metadata.
- `apps/connector-hub/sandbox/`: sandbox definitions.
- `scripts/validate-connector-sandbox.py`: validation entrypoint.

## Example

List connector manifest IDs:

```bash
rg -n "id:" apps/connector-hub/registry
```

## Next steps

- Implement registry APIs under `apps/connector-hub/src/`.
- Add auth and audit logging via `services/identity-access/` and `services/audit-log/`.
