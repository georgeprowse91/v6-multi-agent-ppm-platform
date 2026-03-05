# Documentation

> Canonical documentation for the multi-agent PPM platform. Each subdirectory contains a hub `README.md` that consolidates all topic files with a linked table of contents.

## Quick navigation

| Area | Hub document | What's inside |
| --- | --- | --- |
| [Architecture](./architecture/README.md) | [architecture/README.md](./architecture/README.md) | System context, logical/physical/deployment design, AI and agent layers, data, connectors, security, observability, resilience, performance, tenancy, and ADR index |
| [Agents](./agents/README.md) | [agents/README.md](./agents/README.md) | Specifications for all 25 agents across 4 domains, integration service taxonomy, configuration reference |
| [API](./api/README.md) | [api/README.md](./api/README.md) | Authentication (JWT/OIDC/SAML/SCIM), event contracts, API governance, webhooks |
| [Connectors](./connectors/README.md) | [connectors/README.md](./connectors/README.md) | 38 connector overview, auth patterns, data mapping, REST config, certification, maturity rubric, M365 mappings, IoT spec, MCP connector docs |
| [Compliance](./compliance/README.md) | [compliance/README.md](./compliance/README.md) | Controls mapping, data classification, retention, DPIA, threat model, audit evidence, certification evidence, financial-services template |
| [Runbooks](./runbooks/README.md) | [runbooks/README.md](./runbooks/README.md) | Quick start, deployment, on-call, monitoring, SLOs/SLIs, incident response, troubleshooting, LLM degradation, data-sync failures, backup/recovery, disaster recovery, secrets, schema rollback, credentials, Compose profiles |
| [Data](./data/README.md) | [data/README.md](./data/README.md) | Canonical data model, data quality rules, lineage events |
| [Methodology](./methodology/README.md) | [methodology/README.md](./methodology/README.md) | Predictive (waterfall), adaptive (Agile/Scrum), and hybrid delivery methodologies |
| [Production Readiness](./production-readiness/README.md) | [production-readiness/README.md](./production-readiness/README.md) | Pre-release checklist, maturity model, assessment, release process, security baseline, evidence pack, maturity scorecards |
| [Testing](./testing/README.md) | [testing/README.md](./testing/README.md) | Acceptance and test strategy, test dependency matrix, CI profile rules |
| [UI](./ui/README.md) | [ui/README.md](./ui/README.md) | Component reference, coverage matrix, known gaps |
| [Change Management](./change-management/README.md) | [change-management/README.md](./change-management/README.md) | Implementation and change plan, training curriculum |
| [Platform Description](./platform-description.md) | [platform-description.md](./platform-description.md) | Product strategy, scope, requirements, personas, UX guidelines, methodology flows, template catalog |
| [Platform Commercials](./platform-commercials.md) | [platform-commercials.md](./platform-commercials.md) | Market analysis, competitive positioning, GTM plan, packaging and pricing, sales enablement |
| [Platform User Guide](./platform-userguide.md) | [platform-userguide.md](./platform-userguide.md) | AI assistant panel guide, prompt library, web console walkthroughs |
| [Templates](./templates/template-index.md) | [templates/template-index.md](./templates/template-index.md) | 100+ project management templates (risk registers, sprint planning, charters, etc.) |
| [Generated Services](./generated/services/README.md) | [generated/services/README.md](./generated/services/README.md) | Auto-generated FastAPI endpoint references per microservice |

## Standalone reference files

| File | Description |
| --- | --- |
| [versioning.md](./versioning.md) | API and documentation versioning policy |
| [solution-index.md](./solution-index.md) | Cross-cutting solution index |
| [design-system.md](./design-system.md) | Design system token guidelines |
| [demo-environment.md](./demo-environment.md) | Demo environment setup and cloud provisioning guide |
| [onboarding/developer-onboarding.md](./onboarding/developer-onboarding.md) | Developer onboarding guide |
| [frontend-spa-migration.md](./frontend-spa-migration.md) | SPA route migration map and state baseline |
| [schema-compatibility-matrix.md](./schema-compatibility-matrix.md) | Schema versioning compatibility matrix |
| [outbound_dependency_inventory.md](./outbound_dependency_inventory.md) | Inventory of outbound HTTP clients and LLM providers |
| [merge-conflict-troubleshooting.md](./merge-conflict-troubleshooting.md) | Guide for resolving merge conflicts |
| [react-native-typescript-alignment.md](./react-native-typescript-alignment.md) | React Native and TypeScript version alignment plan |
| [root-file-policy.md](./root-file-policy.md) | Policy governing artefacts allowed at the repository root |
| [dr-runbook.md](./dr-runbook.md) | Standalone disaster recovery runbook (also covered in [runbooks/README.md](./runbooks/README.md)) |
| [CHANGELOG.md](./CHANGELOG.md) | Documentation changelog |

## Generated artefacts

The following files are code-derived and should not be edited manually:

- **Service endpoint references** — [`generated/services/`](./generated/services/)
- **Connector capability matrix** — [`connectors/generated/capability-matrix.md`](./connectors/generated/capability-matrix.md)

Regenerate with:

```bash
python ops/tools/codegen/generate_docs.py
```

## Link validation

Run the link checker to verify all internal markdown links resolve:

```bash
python ops/scripts/check-links.py
```
