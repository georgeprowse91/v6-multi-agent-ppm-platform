# Template Library (Canonical Index)

This folder contains a canonical, modular template system:
- **Base templates** in `core/*/base.yaml`
- **Methodology extensions** in `extensions/<methodology>/*.patch.yaml`
- **Machine-readable index** in [`index.json`](./index.json)

## How to choose (quick guide)

1. **Pick your discipline** (delivery governance, product engineering, operations).
2. **Select a base template** that matches the primary artefact.
3. **Apply a methodology extension** (Adaptive, SAFe, Hybrid, Predictive, DevOps, Compliance Privacy) when needed.
4. **Check migration notes** if coming from legacy Markdown templates.

Useful links:
- Base templates: [](./core/)
- Methodology extensions: [](./extensions/)
- Migration table (legacy → canonical): [Template Naming Rules](./standards/template-naming-rules.md#4-examples-legacy--canonical-mappings#4-examples-legacy--canonical-mappings)
- Deprecation policy: [Index Governance](./standards/index-governance.md#deprecate-or-retire-a-template#deprecate-or-retire-a-template)
- Retirement changelog: [`CHANGELOG.md`](./CHANGELOG.md)

## Legacy transition policy (redirect stubs)

Legacy template files listed in `migration/legacy-to-canonical.csv` remain at their original paths during the transition period as **redirect stubs**.

- Stub files include the marker string `MIGRATION_STUB` for automated detection.
- Each stub must declare:
  - `Deprecated: use <canonical target>`
  - deprecation timeline/date from `deprecation_timeline`
  - links to canonical manifest/template and extension patch guidance (where applicable)
- During transition, the legacy path stays in place to preserve compatibility for links and automation.
- Physical file deletion happens only after the retirement date in the migration table.

## Legacy alias registry (deterministic resolution)

The following aliases are maintained as **one-to-one** mappings to canonical template IDs in both template metadata and `index.json` historical entries.

| Legacy file | Canonical template ID | Lifecycle |
|---|---|---|
| `project_charter_template.md` | `project-charter.universal.v1` | deprecated legacy alias |
| `project_management_plan_template.md` | `project-management-plan.universal.v1` | deprecated legacy alias |
| `risk_register_template.md` | `risk-register.universal.v1` | deprecated legacy alias |
| `status-report-template.md` | `status-report.universal.v1` | deprecated legacy alias |
| `product_backlog_template.md` | `product-backlog.universal.v1` | deprecated legacy alias |


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

### Adaptive extensions

- [Product Backlog.patch](extensions/agile/product-backlog.patch.yaml)
- [Project Charter.patch](extensions/compliance/privacy/project-charter.patch.yaml)
- [Risk Register.patch](extensions/agile/risk-register.patch.yaml)
- [Sprint Planning.patch](extensions/agile/sprint-planning.patch.yaml)
- [Sprint Retrospective.patch](extensions/agile/sprint-retrospective.patch.yaml)
- [Sprint Review.patch](extensions/agile/sprint-review.patch.yaml)
- [Status Report.patch](extensions/waterfall/status-report.patch.yaml)

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

### Predictive extensions

- [Project Charter.patch](extensions/compliance/privacy/project-charter.patch.yaml)
- [Project Management Plan.patch](extensions/waterfall/project-management-plan.patch.yaml)
- [Requirements.patch](extensions/waterfall/requirements.patch.yaml)
- [Status Report.patch](extensions/waterfall/status-report.patch.yaml)

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
