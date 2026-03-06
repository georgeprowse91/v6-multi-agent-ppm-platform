# Documentation

> Canonical documentation for the multi-agent PPM platform. Each subdirectory contains a hub `README.md` that consolidates all topic files with a linked table of contents.

## Quick navigation

| Area | Hub document | What's inside |
| --- | --- | --- |
| [Architecture](./architecture/README.md) | [Readme](./architecture/README.md) | System context, logical/physical/deployment design, AI and agent layers, data, connectors, security, observability, resilience, performance, tenancy, and ADR index |
| [Readme](README.md) | [Readme](README.md) | Specifications for all 25 agents across 4 domains, integration service taxonomy, configuration reference |
| [API](./api/README.md) | [Readme](./api/README.md) | Authentication (JWT/OIDC/SAML/SCIM), event contracts, API governance, webhooks |
| [Connectors](./connectors/README.md) | [Readme](./connectors/README.md) | 38 connector overview, auth patterns, data mapping, REST config, certification, maturity rubric, M365 mappings, IoT spec, MCP connector docs |
| [Readme](README.md) | [Readme](README.md) | Controls mapping, data classification, retention, DPIA, threat model, audit evidence, certification evidence, financial-services template |
| [Readme](README.md) | [Readme](README.md) | Quick start, deployment, on-call, monitoring, SLOs/SLIs, incident response, troubleshooting, LLM degradation, data-sync failures, backup/recovery, disaster recovery, secrets, schema rollback, credentials, Compose profiles |
| [Readme](README.md) | [Readme](README.md) | Canonical data model, data quality rules, lineage events |
| [Methodology](./methodology/README.md) | [Readme](./methodology/README.md) | Predictive (waterfall), adaptive (Agile/Scrum), and hybrid delivery methodologies |
| [Production Readiness](./production-readiness/README.md) | [Readme](./production-readiness/README.md) | Pre-release checklist, maturity model, assessment, release process, security baseline, evidence pack, maturity scorecards |
| [Testing](./testing/README.md) | [Readme](./testing/README.md) | Acceptance and test strategy, test dependency matrix, CI profile rules |
| [Readme](assets/ui/screenshots/README.md) | [Readme](assets/ui/screenshots/README.md) | Component reference, coverage matrix, known gaps |
| [Readme](README.md) | [Readme](README.md) | Implementation and change plan, training curriculum |
| [Platform Description](./platform-description.md) | [Platform Description](./platform-description.md) | Product strategy, scope, requirements, personas, UX guidelines, methodology flows, template catalog |
| [Platform Commercials](./platform-commercials.md) | [Platform Commercials](./platform-commercials.md) | Market analysis, competitive positioning, GTM plan, packaging and pricing, sales enablement |
| [Platform User Guide](./platform-userguide.md) | [Platform Userguide](./platform-userguide.md) | AI assistant panel guide, prompt library, web console walkthroughs |
| [Templates](./templates/template-index.md) | [Template Index](./templates/template-index.md) | 100+ project management templates (risk registers, sprint planning, charters, etc.) |
| [Generated Services](./generated/services/README.md) | [Readme](./generated/services/README.md) | Auto-generated FastAPI endpoint references per microservice |

## Standalone reference files

| File | Description |
| --- | --- |
| [Versioning](./versioning.md) | API and documentation versioning policy |
| [Solution Index](./solution-index.md) | Cross-cutting solution index |
| [Design System](./design-system.md) | Design system token guidelines |
| [Demo Environment](./demo-environment.md) | Demo environment setup and cloud provisioning guide |
| [Developer Onboarding](./onboarding/developer-onboarding.md) | Developer onboarding guide |
| [Frontend Spa Migration](./frontend-spa-migration.md) | SPA route migration map and state baseline |
| [Schema Compatibility Matrix](./schema-compatibility-matrix.md) | Schema versioning compatibility matrix |
| [Outbound Dependency Inventory](./outbound_dependency_inventory.md) | Inventory of outbound HTTP clients and LLM providers |
| [Merge Conflict Troubleshooting](./merge-conflict-troubleshooting.md) | Guide for resolving merge conflicts |
| [React Native Typescript Alignment](./react-native-typescript-alignment.md) | React Native and TypeScript version alignment plan |
| [Root File Policy](./root-file-policy.md) | Policy governing artefacts allowed at the repository root |
| [Dr Runbook](./dr-runbook.md) | Standalone disaster recovery runbook (also covered in [Readme](README.md)) |
| [Changelog](./CHANGELOG.md) | Documentation changelog |

## Generated artefacts

The following files are code-derived and should not be edited manually:

- **Service endpoint references** — [Services](generated/services/README.md)
- **Connector capability matrix** — [Capability Matrix](./connectors/generated/capability-matrix.md)

Regenerate with:

```bash
python ops/tools/codegen/generate_docs.py
```

## Link validation

Run the link checker to verify all internal markdown links resolve:

```bash
python ops/scripts/check-links.py
```
