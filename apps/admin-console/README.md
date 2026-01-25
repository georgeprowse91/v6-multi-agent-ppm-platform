# Admin Console

Administrative UI for tenant setup, permissions, and governance workflows.

## Current state

- UI scaffolding and deployment assets are tracked under `apps/admin-console/`.
- No runtime server is wired in this repo yet; this app is an initial scaffold for the eventual UI.

## Quickstart

List deployment assets:

```bash
ls apps/admin-console
```

## How to verify

```bash
ls apps/admin-console/helm
```

Expected output includes Helm chart templates for the admin console deployment.

## Key files

- `apps/admin-console/helm/`: deployment manifests.
- `apps/admin-console/tests/`: test scaffolding for the UI.

## Example

Search for the admin console name in deployment manifests:

```bash
rg -n "admin" apps/admin-console/helm
```

## Next steps

- Implement UI sources under `apps/admin-console/src/`.
- Wire auth flows via `services/identity-access/`.
