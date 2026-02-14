# Template Taxonomy Standard

## Purpose
This standard defines a shared taxonomy for all templates under `docs/templates/` so templates can be discovered, validated, and versioned consistently.

## 1) Primary Artefact Classes
Use one `artefact` class as the leading canonical identifier for every template.

| Artefact class | Description | Typical outputs |
|---|---|---|
| `business-case` | Justification of investment, expected value, and options. | ROI analysis, benefit-cost narrative, investment memo |
| `charter` | Authorization document defining scope, authority, and objectives. | Project charter, program charter, team charter |
| `risk-register` | Structured risk inventory with scoring and response plans. | IT risk register, healthcare risk register |
| `roadmap` | Time-sequenced plan of initiatives, releases, or capabilities. | Product roadmap, technology adoption roadmap |
| `compliance-assessment` | Evaluation of controls against standards/regulations. | GxP checklist, governance/compliance gap assessment |
| `plan` | Actionable execution plan across scope, schedule, quality, or change. | PM plan, quality plan, test plan, migration plan |
| `report` | Status or outcome communication artefact. | Executive status report, closure report |
| `register` | Structured log of entities (stakeholders, issues, actions). | Stakeholder register, issue log |
| `assessment` | Scored diagnostic of maturity, health, readiness, or risk posture. | Maturity assessment, health assessment |
| `backlog` | Prioritized work items or demand queue. | Product backlog, program backlog |
| `protocol` | Prescriptive procedural template used in regulated operations. | Validation protocol, qualification protocol |
| `matrix` | Cross-referenced decision/support table. | Traceability matrix, controls matrix |
| `dashboard` | Template for KPI/metric visualization structures. | Executive dashboard, metrics dashboard |
| `checklist` | Completion or compliance verification list. | Quality checklist, closure checklist |

### Artefact selection rule
If a template appears to fit multiple classes, choose the class representing its **primary decision/use outcome**:
1. What decision does this template support?
2. What is the main consumer workflow?
3. What object is version-controlled over time?

## 2) Variant Dimensions
Variants are optional, composable qualifiers that refine a base artefact.

### 2.1 Methodology (`methodology`)
Allowed examples:
- `adaptive`
- `scrum`
- `safe`
- `predictive`
- `hybrid`
- `lean`
- `kanban`
- `traditional`

### 2.2 Governance tier (`governance_tier`)
Allowed examples:
- `team`
- `project`
- `program`
- `portfolio`
- `enterprise`

### 2.3 Regulation scope (`regulation_scope`)
Allowed examples:
- `none`
- `gxp`
- `iso27001`
- `sox`
- `gdpr`
- `hipaa`
- `pci-dss`
- `fda-21cfr11`

### 2.4 Industry (`industry`)
Allowed examples:
- `cross-industry`
- `software`
- `construction`
- `healthcare`
- `pharmaceutical`
- `financial-services`
- `manufacturing`
- `public-sector`

### Variant formatting
- Use lowercase kebab-case values.
- Multi-variant composition order for identifiers should be:
  1. `methodology`
  2. `governance_tier`
  3. `regulation_scope`
  4. `industry`
- Omit unset dimensions rather than inserting placeholders.

## 3) ID Convention and Filename Pattern

### Canonical template ID
`template_id` format:

```text
<artefact>[.<methodology>][.<governance_tier>][.<regulation_scope>][.<industry>].v<major>[.<minor>]
```

Examples:
- `charter.adaptive.project.software.v1`
- `risk-register.hybrid.program.gdpr.financial-services.v2.1`
- `compliance-assessment.enterprise.gxp.pharmaceutical.v1`

### Canonical filename
Filename format:

```text
<artefact>[.<methodology>][.<governance_tier>][.<regulation_scope>][.<industry>].v<major>[.<minor>].yaml
```

Example compatible with requested style:
- `<artefact>.<variant>.<version>.yaml`

Concrete examples:
- `business-case.traditional.project.cross-industry.v1.yaml`
- `charter.hybrid.program.financial-services.v1.yaml`
- `risk-register.safe.portfolio.software.v2.yaml`

### Notes for markdown templates
If content remains in Markdown, keep the same canonical stem and switch extension only:
- `.yaml` for structured metadata-first templates
- `.md` for narrative templates

Example:
- `roadmap.adaptive.portfolio.software.v1.md`

## 4) Lightweight Maintainer Lint Checklist
Use this checklist manually or as script acceptance criteria.

- [ ] Filename matches canonical regex:  
      `^[a-z0-9-]+(\.[a-z0-9-]+){1,5}\.v[0-9]+(\.[0-9]+)?\.(yaml|md)$`
- [ ] `artefact` class is one of the approved primary classes.
- [ ] Variant values are kebab-case and from approved vocabularies (or explicitly documented extension).
- [ ] Variant ordering follows: methodology → governance tier → regulation scope → industry.
- [ ] Version segment is present and semantic (`v1`, `v2.1`, etc.).
- [ ] `template_id` in metadata exactly matches filename stem (excluding extension).
- [ ] If replacing a legacy file, a compatibility alias is captured in naming rules.
- [ ] Deprecated aliases include sunset version/date and migration target.
