# Scripts

## Overview

This directory contains repository maintenance scripts used by CI pipelines and local development workflows. Scripts handle documentation validation, schema checking, security verification, database setup, and other automation tasks. They are called from the Makefile and CI workflows.

## Key files

| File | Description |
| --- | --- |
| [check-links.py](./check-links.py) | Validates internal documentation links |
| [check-migrations.py](./check-migrations.py) | Checks database migration consistency |
| [check-placeholders.py](./check-placeholders.py) | Detects unresolved placeholders in configuration files |
| [check-templates.py](./check-templates.py) | Validates template assets |
| [check-ui-emojis.sh](./check-ui-emojis.sh) | Checks UI files for emoji usage |
| [check-ui-icons.sh](./check-ui-icons.sh) | Checks UI files for icon usage |
| [check_api_versioning.py](./check_api_versioning.py) | Validates API versioning conventions |
| [compare_benchmarks.py](./compare_benchmarks.py) | Compares performance benchmark results |
| [connector-certification.py](./connector-certification.py) | Runs connector certification checks |
| [db_backup.sh](./db_backup.sh) | Database backup utility |
| [export_audit_evidence.py](./export_audit_evidence.py) | Exports audit evidence artifacts |
| [fix_docs_formatting.py](./fix_docs_formatting.py) | Fixes documentation formatting issues |
| [generate-sbom.py](./generate-sbom.py) | Generates software bill of materials (SBOM) |
| [init-db.sql](./init-db.sql) | Database initialization schema |
| [load-test.py](./load-test.py) | Load testing runner |
| [quickstart_smoke.py](./quickstart_smoke.py) | Quickstart smoke test |
| [rotate_secrets.sh](./rotate_secrets.sh) | Secret rotation utility |
| [sign-artifact.py](./sign-artifact.py) | Artifact signing script |
| [validate-analytics-jobs.py](./validate-analytics-jobs.py) | Validates analytics job definitions |
| [validate-connector-sandbox.py](./validate-connector-sandbox.py) | Validates connector sandbox configuration |
| [validate-examples.py](./validate-examples.py) | Validates example files |
| [validate-github-workflows.py](./validate-github-workflows.py) | Validates GitHub workflow definitions |
| [validate-helm-charts.py](./validate-helm-charts.py) | Validates Helm chart structure |
| [validate-intent-routing.py](./validate-intent-routing.py) | Validates intent routing configuration |
| [validate-manifests.py](./validate-manifests.py) | Validates deployment manifests |
| [validate-policies.py](./validate-policies.py) | Validates policy definitions |
| [validate-prompts.py](./validate-prompts.py) | Validates agent prompt templates |
| [validate-schemas.py](./validate-schemas.py) | Validates JSON/YAML schemas |
| [validate-workflows.py](./validate-workflows.py) | Validates workflow definitions |
| [validate_config.py](./validate_config.py) | Validates configuration files |
| [verify-production-readiness.sh](./verify-production-readiness.sh) | Verifies production readiness criteria |
| [verify-signature.py](./verify-signature.py) | Verifies artifact signatures |
| [verify_manifest.py](./verify_manifest.py) | Verifies deployment manifest integrity |

## How to run / develop / test

Run scripts directly with Python or Bash from the repository root:

```bash
python scripts/check-links.py
python scripts/validate-schemas.py
```

## Configuration

Scripts rely on repository structure; no additional configuration required.

## Troubleshooting

- Script fails: ensure the required dependencies are installed.
- Path errors: run scripts from the repository root.
