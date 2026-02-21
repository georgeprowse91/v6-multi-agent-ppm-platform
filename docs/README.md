# Documentation Hub

## Overview

This directory contains the canonical documentation set for the multi-agent PPM platform. It covers architecture narratives, API contracts, agent specifications, compliance guidance, onboarding material, operational runbooks, and shared templates. These documents are referenced by the root README and provide the authoritative explanations for the platform architecture, data model, and operating procedures.

## Directory structure

| Folder | Description |
| --- | --- |
| [agents/](./agents/) | Agent specifications and catalog |
| [api/](./api/) | API schemas, OpenAPI specs, and contracts |
| [architecture/](./architecture/) | Architecture narratives, diagrams, and ADRs |
| [assets/ui/screenshots/](./assets/ui/screenshots/) | Centralized UI screenshots for documentation |
| [change-management/](./change-management/) | Change management training plan and adoption guidance |
| [compliance/](./compliance/) | Compliance guidance, DPIA, threat model |
| [connectors/](./connectors/) | Connector documentation and integration guides |
| [generated/services/](./generated/services/) | Generated FastAPI endpoint references per service |
| [connectors/generated/](./connectors/generated/) | Generated connector capability docs from manifests + maturity inventory |
| [data/](./data/) | Data model, quality, and lineage docs |
| [dependencies/](./dependencies/) | Dependency management policy and inventory |
| [methodology/](./methodology/) | Methodology maps (adaptive, predictive, hybrid) with templates |
| [onboarding/](./onboarding/) | Developer onboarding guides |
| [product/](./product/) | Product documentation, personas, user guides |
| [production-readiness/](./production-readiness/) | Release checklists and evidence packs |
| [runbooks/](./runbooks/) | Operational runbooks |
| [templates/](./templates/) | Shared template library |
| [testing/](./testing/) | Test dependency matrix and testing strategy |
| [ui/](./ui/) | UI route coverage matrix and gap analysis |

## Key files

| File | Description |
| --- | --- |
| [versioning.md](./versioning.md) | API and documentation versioning policy |
| [solution-index.md](./solution-index.md) | Cross-cutting solution index |
| [dr-runbook.md](./dr-runbook.md) | Disaster recovery runbook |
| [design-system.md](./design-system.md) | Design system token guidelines |
| [demo-environment.md](./demo-environment.md) | Demo environment setup and cloud provisioning guide |
| [frontend-spa-migration.md](./frontend-spa-migration.md) | SPA route migration map and state baseline |
| [merge-conflict-troubleshooting.md](./merge-conflict-troubleshooting.md) | Guide for resolving merge conflicts |
| [outbound_dependency_inventory.md](./outbound_dependency_inventory.md) | Inventory of outbound HTTP clients and LLM providers |
| [react-native-typescript-alignment.md](./react-native-typescript-alignment.md) | React/React Native/TypeScript version alignment plan |
| [root-file-policy.md](./root-file-policy.md) | Policy governing artifacts allowed at the repository root |
| [schema-compatibility-matrix.md](./schema-compatibility-matrix.md) | Schema versioning compatibility matrix and CLI tooling |

## Onboarding & release references

- Developer onboarding guide: [docs/onboarding/developer-onboarding.md](./onboarding/developer-onboarding.md)
- Release process: [docs/production-readiness/release-process.md](./production-readiness/release-process.md)
- Operational runbooks: [docs/runbooks/](./runbooks/)

## How to run / develop / test

Validate internal links across docs:

```bash
python scripts/check-links.py
```

## Configuration

No configuration. Documentation content lives in Markdown and YAML files under this folder.

## Troubleshooting

- Broken links: run the link checker and fix any relative path mismatches.
- Missing diagrams: verify files exist under `docs/architecture/diagrams/` where referenced.

## Generated artifacts

The following docs are code-derived and should be treated as source of truth:

- Service endpoints: [`docs/generated/services/`](./generated/services/)
- Connector capabilities: [`docs/connectors/generated/capability-matrix.md`](./connectors/generated/capability-matrix.md)

Regenerate them with:

```bash
python ops/tools/codegen/generate_docs.py
```
