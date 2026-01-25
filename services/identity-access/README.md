# Identity & Access Service

IAM, RBAC enforcement, and tenant identity integration.

## Current state

- Helm chart under `services/identity-access/helm/`.
- Source scaffolding under `services/identity-access/src/`.
- No runtime service implementation yet.

## Quickstart

Validate the Helm chart:

```bash
python scripts/validate-helm-charts.py services/identity-access/helm
```

## How to verify

```bash
ls services/identity-access/src
```

Expected output lists source scaffolding files.

## Key files

- `services/identity-access/helm/`: deployment assets.
- `services/identity-access/src/`: IAM service scaffolding.

## Example

Search for RBAC references:

```bash
rg -n "rbac|role" services/identity-access
```

## Next steps

- Implement OAuth/OIDC flows in `services/identity-access/src/`.
- Integrate tenant configuration from `config/tenants/`.
