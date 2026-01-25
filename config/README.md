# Configuration

Centralized configuration for tenants, environments, and platform defaults.

## Contents
- `tenants/`: Tenant-specific configuration and provisioning templates.

## Guidance
Store non-secret configuration here. Secrets should be provided via environment variables or
secret stores and referenced in `.env.example`.
