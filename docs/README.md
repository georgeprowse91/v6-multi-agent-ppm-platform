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
| [compliance/](./compliance/) | Compliance guidance, DPIA, threat model |
| [connectors/](./connectors/) | Connector documentation and integration guides |
| [data/](./data/) | Data model, quality, and lineage docs |
| [methodology/](./methodology/) | Methodology maps (adaptive, predictive, hybrid) with templates |
| [onboarding/](./onboarding/) | Developer onboarding guides |
| [product/](./product/) | Product documentation, personas, user guides |
| [production-readiness/](./production-readiness/) | Release checklists and evidence packs |
| [runbooks/](./runbooks/) | Operational runbooks |
| [templates/](./templates/) | Shared template library |

## Key files

| File | Description |
| --- | --- |
| [versioning.md](./versioning.md) | API and documentation versioning policy |
| [solution-index.md](./solution-index.md) | Cross-cutting solution index |
| [dr-runbook.md](./dr-runbook.md) | Disaster recovery runbook |
| [design-system.md](./design-system.md) | Design system guidelines |
| [merge-conflict-troubleshooting.md](./merge-conflict-troubleshooting.md) | Guide for resolving merge conflicts |

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
