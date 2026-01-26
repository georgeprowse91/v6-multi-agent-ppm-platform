# Policy Engine: Policies

## Purpose

Document the policies assets owned by the Policy Engine service.

## What's inside

- `services/policy-engine/policies/bundles`: Subdirectory containing bundles assets for this area.
- `services/policy-engine/policies/schema`: Schemas or validation rules for component assets.

## How it's used

These assets are consumed by the service runtime or deployment tooling.

## How to run / develop / test

```bash
ls services/policy-engine/policies
```

## Configuration

Configuration is inherited from the parent service and `.env` settings.

## Troubleshooting

- Missing asset files: ensure the parent service references valid paths.
- Validation failures: confirm schema compatibility with the parent service.
