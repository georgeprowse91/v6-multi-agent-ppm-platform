# Template Consolidation Map

## Scope and approach
This audit reviewed `docs/templates/**` and grouped near-duplicate templates by artefact intent. Consolidation keeps one canonical base in `docs/templates/core/<artefact>/base.yaml` and moves methodology-specific differences into overlay files in `docs/templates/extensions/<methodology>/<artefact>.patch.yaml`.

## Consolidation groups

| Artefact intent | Canonical base | Methodology extensions | Near-duplicate legacy files to retire |
|---|---|---|---|
| Project Charter | `core/project-charter/manifest.yaml` | Adaptive, Predictive, Hybrid | `project_charter_template.md`, `project-charter-example.md`, `project-charter-software-example.md`, `software-project-charter.md`, `traditional-project-charter-template.md`, `it-project-charter.md`, `construction-project-charter.md`, `clinical-trial-project-charter.md`, `financial_services_project_charter.md`, `hybrid_project_charter_template.md` |
| Risk Register / Risk Log | `core/risk-register/manifest.yaml` | Adaptive, Hybrid | `risk-register.md`, `risk_register_template.md`, `software-risk-register.md`, `it-risk-register.md`, `construction-risk-register.md`, `healthcare-risk-register.md`, `adaptive-risk-board-template.md`, `raid_log_template.md` |
| Status Reporting | `core/status-report/manifest.yaml` | Adaptive, Predictive, Hybrid, SAFe | `status-report-template.md`, `status-report.md`, `status-report-example.md`, `project_execution_status_report_template.md`, `executive-status-report.md` |
| Communication Planning | `core/communication-plan/manifest.yaml` | (future: Adaptive/Predictive/Hybrid overlays) | `communication-plan.md`, `communication_plan_template.md`, `stakeholder_communication_planning.md`, `stakeholder-update.md` |
| Project Management Plan (PMP) | `core/project-management-plan/manifest.yaml` | Predictive, Hybrid | `project_management_plan_template.md`, `project-management-plan-example.md`, `traditional-project-management-plan-template.md`, `hybrid-project-management-plan-template.md`, `program_management_plan_template.md` |
| Requirements | `core/requirements/manifest.yaml` | Predictive | `requirements_specification_template.md`, `software-requirements-specification-template.md`, `business_requirements_document_template.md`, `requirements_traceability_matrix_template.md` |
| Sprint Planning | `core/sprint-planning/manifest.yaml` | Adaptive, SAFe | `sprint-planning-template.md`, `sprint_planning_example.md`, `less_sprint_planning_template.md`, `pi_planning_template.md` |
| Sprint Review | `core/sprint-review/manifest.yaml` | Adaptive | `sprint-review-template.md`, `sprint_review_example.md` |
| Sprint Retrospective | `core/sprint-retrospective/manifest.yaml` | Adaptive | `sprint-retrospective-template.md`, `sprint_retrospective_example.md`, `less_retrospective_template.md` |
| Product Backlog | `core/product-backlog/manifest.yaml` | Adaptive, SAFe | `product_backlog_template.md`, `overall_product_backlog_template.md`, `product_backlog_example.md`, `backlog-management-template.md`, `backlog-refinement-template.md` |
| Deployment Checklist | `core/deployment-checklist/manifest.yaml` | (future: environment-specific overlays) | `deployment-checklist.md`, `deployment-checklist-template.md` |
| Executive Dashboard | `core/executive-dashboard/manifest.yaml` | SAFe | `executive-dashboard.md`, `executive-dashboard-template.md`, `executive-dashboard-workbook.md`, `executive-dashboard-slides.md`, `Executive-Report-Templates.md` |

## Overlay format
- Overlay files use a patch-style YAML envelope:
  - `extends`: points to the canonical base.
  - `add_sections` / `add_fields` / `add_tiles`: additive deltas.
  - `replace`: optional key-level substitutions.
- This allows one baseline artefact per intent with explicit, auditable methodology variation.

## Deprecation timeline
1. **Announce (immediate)**: Publish consolidation map and mapping CSV.
2. **Transition (2026-03-31)**: Keep legacy templates read-only; direct new usage to canonical paths.
3. **Retire (2026-06-30)**: Remove retired legacy duplicates after one full quarter of migration support.
