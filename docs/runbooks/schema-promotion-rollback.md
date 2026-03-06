# Schema Promotion Rollback Runbook

Procedures for rolling back schema changes in the PPM platform.

## Overview

Schema changes are promoted through environments (dev -> staging -> production) using Alembic migrations. This runbook covers rollback procedures when a schema change causes issues.

## Rollback Procedure

### 1. Identify the Problem Migration

1. Check the current migration head:
   ```bash
   alembic current
   ```
2. Review recent migration history:
   ```bash
   alembic history --verbose
   ```
3. Identify the migration version that introduced the issue.

### 2. Execute Rollback

1. Downgrade to the previous migration version:
   ```bash
   alembic downgrade -1
   ```
2. For multiple migrations:
   ```bash
   alembic downgrade <target-revision>
   ```

### 3. Deploy Compatible Application Version

1. Roll back the application deployment to match the schema:
   ```bash
   helm rollback ppm-platform <compatible-revision> -n ppm
   ```
2. Verify the application starts without migration errors.

## Verification Checklist

After rollback, verify the following:

- [ ] All services start successfully.
- [ ] Health endpoints return `status: ok`.
- [ ] Data queries return expected results.
- [ ] No schema mismatch errors in application logs.
- [ ] API contract tests pass against the rolled-back schema.
- [ ] Connector sync jobs complete without errors.

## Prevention

1. Always test migrations in staging before production.
2. Ensure every migration has a working downgrade path.
3. Run `make migration-check` as part of the CI pipeline.
4. Keep migration files small and focused on single changes.
