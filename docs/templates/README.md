# Template Library (Canonical Index)

This folder contains a canonical, modular template system:
- **Base templates** in `core/*/base.yaml`
- **Methodology extensions** in `extensions/<methodology>/*.patch.yaml`
- **Machine-readable index** in [`index.json`](./index.json)

## How to choose (quick guide)

1. **Pick your discipline** (delivery governance, product engineering, operations).
2. **Select a base template** that matches the primary artefact.
3. **Apply a methodology extension** (Agile, SAFe, Hybrid, Waterfall, DevOps, Compliance Privacy) when needed.
4. **Check migration notes** if coming from legacy Markdown templates.

Useful links:
- Base templates: [`core/`](./core/)
- Methodology extensions: [`extensions/`](./extensions/)
- Migration table (legacy → canonical): [`standards/template-naming-rules.md#4-examples-legacy--canonical-mappings`](./standards/template-naming-rules.md#4-examples-legacy--canonical-mappings)

## Category index by discipline

### Delivery governance

| Template | Type | Base |
|---|---|---|
| [Project Charter](./core/project-charter/manifest.yaml) | Charter | ✅ |
| [Project Management Plan](./core/project-management-plan/manifest.yaml) | Plan | ✅ |
| [Status Report](./core/status-report/manifest.yaml) | Report | ✅ |
| [Risk Register](./core/risk-register/manifest.yaml) | Risk Register | ✅ |
| [Communication Plan](./core/communication-plan/manifest.yaml) | Plan | ✅ |

### Product & engineering delivery

| Template | Type | Base |
|---|---|---|
| [Product Backlog](./core/product-backlog/manifest.yaml) | Backlog | ✅ |
| [Requirements](./core/requirements/manifest.yaml) | Plan | ✅ |
| [Sprint Planning](./core/sprint-planning/manifest.yaml) | Plan | ✅ |
| [Sprint Review](./core/sprint-review/manifest.yaml) | Report | ✅ |
| [Sprint Retrospective](./core/sprint-retrospective/manifest.yaml) | Report | ✅ |

### Operations & executive oversight

| Template | Type | Base |
|---|---|---|
| [Executive Dashboard](./core/executive-dashboard/manifest.yaml) | Dashboard | ✅ |
| [Deployment Checklist](./core/deployment-checklist/manifest.yaml) | Checklist | ✅ |

## Category index by methodology

### Universal (base only)

- [communication-plan.universal.v1](./core/communication-plan/manifest.yaml)
- [deployment-checklist.universal.v1](./core/deployment-checklist/manifest.yaml)
- [executive-dashboard.universal.v1](./core/executive-dashboard/manifest.yaml)
- [product-backlog.universal.v1](./core/product-backlog/manifest.yaml)
- [project-charter.universal.v1](./core/project-charter/manifest.yaml)
- [project-management-plan.universal.v1](./core/project-management-plan/manifest.yaml)
- [requirements.universal.v1](./core/requirements/manifest.yaml)
- [risk-register.universal.v1](./core/risk-register/manifest.yaml)
- [sprint-planning.universal.v1](./core/sprint-planning/manifest.yaml)
- [sprint-retrospective.universal.v1](./core/sprint-retrospective/manifest.yaml)
- [sprint-review.universal.v1](./core/sprint-review/manifest.yaml)
- [status-report.universal.v1](./core/status-report/manifest.yaml)

### Agile extensions

- [product-backlog.agile.v1](./extensions/agile/product-backlog.patch.yaml)
- [project-charter.agile.v1](./extensions/agile/project-charter.patch.yaml)
- [risk-register.agile.v1](./extensions/agile/risk-register.patch.yaml)
- [sprint-planning.agile.v1](./extensions/agile/sprint-planning.patch.yaml)
- [sprint-retrospective.agile.v1](./extensions/agile/sprint-retrospective.patch.yaml)
- [sprint-review.agile.v1](./extensions/agile/sprint-review.patch.yaml)
- [status-report.agile.v1](./extensions/agile/status-report.patch.yaml)

### SAFe extensions

- [executive-dashboard.safe.v1](./extensions/safe/executive-dashboard.patch.yaml)
- [product-backlog.safe.v1](./extensions/safe/product-backlog.patch.yaml)
- [sprint-planning.safe.v1](./extensions/safe/sprint-planning.patch.yaml)
- [risk-register.safe.v1](./extensions/safe/risk-register.patch.yaml)
- [status-report.safe.v1](./extensions/safe/status-report.patch.yaml)

### DevOps extensions

- [deployment-checklist.devops.v1](./extensions/devops/deployment-checklist.patch.yaml)

### Compliance privacy extensions

- [project-charter.compliance-privacy.v1](./extensions/compliance/privacy/project-charter.patch.yaml)

## Selection guidance (compliance-aware)

- Use **DevOps extensions** when deployment governance needs CI/CD automation, release controls, rollback readiness, and observability evidence.
- Use **SAFe risk extensions** when teams need PI-level risk rollups and ROAM disposition tracking in addition to base risk logging.
- Use **Compliance Privacy extensions** for initiatives processing personal data or handling regulated data flows. Ensure the extension captures:
  - **Data classification** for each personal data category processed.
  - **Legal basis** for processing and jurisdictional applicability.
  - **DPIA trigger assessment** and escalation criteria.
  - **Control evidence references** (control IDs, evidence links, and accountable owners).

### Hybrid extensions

- [project-charter.hybrid.v1](./extensions/hybrid/project-charter.patch.yaml)
- [project-management-plan.hybrid.v1](./extensions/hybrid/project-management-plan.patch.yaml)
- [risk-register.hybrid.v1](./extensions/hybrid/risk-register.patch.yaml)
- [status-report.hybrid.v1](./extensions/hybrid/status-report.patch.yaml)

### Waterfall extensions

- [project-charter.waterfall.v1](./extensions/waterfall/project-charter.patch.yaml)
- [project-management-plan.waterfall.v1](./extensions/waterfall/project-management-plan.patch.yaml)
- [requirements.waterfall.v1](./extensions/waterfall/requirements.patch.yaml)
- [status-report.waterfall.v1](./extensions/waterfall/status-report.patch.yaml)

## Related standards

- [Template taxonomy](./standards/template-taxonomy.md)
- [Template naming rules and migration table](./standards/template-naming-rules.md)
- [Index governance policy](./standards/index-governance.md)
- [Placeholder token standard](./standards/placeholders.md)
- [Template field mapping registry](./mappings/template-field-map.json)

## Binding examples

End-to-end substitution flow for canonical rendering:

1. **Load template structure** from a base file (for example, `core/project-charter/manifest.yaml`).
2. **Resolve placeholders** listed in `placeholders[]` against the mapping registry in `mappings/template-field-map.json`.
3. **Validate source data** using registry data type and validation hints.
4. **Apply fallback policy** (error/default/empty) based on `required` + `fallback.strategy`.
5. **Render sections** using `sections[].consumes_placeholders` to scope substitutions.

Example:

- Template tokens: `{{project_name}}`, `{{total_budget}}`
- Mapping:
  - `{{project_name}}` -> `project.name`
  - `{{total_budget}}` -> `financials.total_budget.amount`
- Input model:

```json
{
  "project": { "name": "ERP Modernization" },
  "financials": { "total_budget": { "amount": 2500000, "currency": "AUD" } }
}
```

- Rendered excerpt:

```text
Project: ERP Modernization
Total Budget: 2500000 AUD
```
