# Templates Changelog

## 2026-02-20 - Legacy template retirement completion

The transition window is closed. The following legacy redirect stubs were removed and now resolve to canonical manifests:

- `docs/templates/project_charter_template.md` → `docs/templates/core/project-charter/manifest.yaml (+ docs/templates/extensions/<methodology>/project-charter.patch.yaml)`
- `docs/templates/project-charter-example.md` → `docs/templates/core/project-charter/manifest.yaml (+ docs/templates/extensions/<methodology>/project-charter.patch.yaml)`
- `docs/templates/project-charter-software-example.md` → `docs/templates/core/project-charter/manifest.yaml (+ docs/templates/extensions/adaptive/project-charter.patch.yaml)`
- `docs/templates/software-project-charter.md` → `docs/templates/core/project-charter/manifest.yaml (+ docs/templates/extensions/adaptive/project-charter.patch.yaml)`
- `docs/templates/traditional-project-charter-template.md` → `docs/templates/core/project-charter/manifest.yaml (+ docs/templates/extensions/predictive/project-charter.patch.yaml)`
- `docs/templates/hybrid_project_charter_template.md` → `docs/templates/core/project-charter/manifest.yaml (+ docs/templates/extensions/hybrid/project-charter.patch.yaml)`
- `docs/templates/it-project-charter.md` → `docs/templates/core/project-charter/manifest.yaml (+ domain appendix)`
- `docs/templates/risk-register.md` → `docs/templates/core/risk-register/manifest.yaml (+ docs/templates/extensions/<methodology>/risk-register.patch.yaml)`
- `docs/templates/risk_register_template.md` → `docs/templates/core/risk-register/manifest.yaml (+ docs/templates/extensions/<methodology>/risk-register.patch.yaml)`
- `docs/templates/software-risk-register.md` → `docs/templates/core/risk-register/manifest.yaml (+ docs/templates/extensions/adaptive/risk-register.patch.yaml)`
- `docs/templates/it-risk-register.md` → `docs/templates/core/risk-register/manifest.yaml (+ domain appendix)`
- `docs/templates/adaptive-risk-board-template.md` → `docs/templates/core/risk-register/manifest.yaml (+ docs/templates/extensions/adaptive/risk-register.patch.yaml)`
- `docs/templates/raid_log_template.md` → `docs/templates/core/risk-register/manifest.yaml (+ optional issue/decision fields)`
- `docs/templates/status-report-template.md` → `docs/templates/core/status-report/manifest.yaml (+ docs/templates/extensions/<methodology>/status-report.patch.yaml)`
- `docs/templates/status-report.md` → `docs/templates/core/status-report/manifest.yaml (+ docs/templates/extensions/<methodology>/status-report.patch.yaml)`
- `docs/templates/status-report-example.md` → `docs/templates/core/status-report/manifest.yaml (+ docs/templates/extensions/<methodology>/status-report.patch.yaml)`
- `docs/templates/project_execution_status_report_template.md` → `docs/templates/core/status-report/manifest.yaml (+ docs/templates/extensions/predictive/status-report.patch.yaml)`
- `docs/templates/executive-status-report.md` → `docs/templates/core/status-report/manifest.yaml (+ executive summary companion)`
- `docs/templates/communication-plan.md` → `docs/templates/core/communication-plan/manifest.yaml`
- `docs/templates/communication_plan_template.md` → `docs/templates/core/communication-plan/manifest.yaml`
- `docs/templates/project_management_plan_template.md` → `docs/templates/core/project-management-plan/manifest.yaml (+ docs/templates/extensions/<methodology>/project-management-plan.patch.yaml)`
- `docs/templates/traditional-project-management-plan-template.md` → `docs/templates/core/project-management-plan/manifest.yaml (+ docs/templates/extensions/predictive/project-management-plan.patch.yaml)`
- `docs/templates/hybrid-project-management-plan-template.md` → `docs/templates/core/project-management-plan/manifest.yaml (+ docs/templates/extensions/hybrid/project-management-plan.patch.yaml)`
- `docs/templates/requirements_specification_template.md` → `docs/templates/core/requirements/manifest.yaml (+ docs/templates/extensions/predictive/requirements.patch.yaml)`
- `docs/templates/software-requirements-specification-template.md` → `docs/templates/core/requirements/manifest.yaml (+ docs/templates/extensions/predictive/requirements.patch.yaml)`
- `docs/templates/sprint-planning-template.md` → `docs/templates/core/sprint-planning/manifest.yaml (+ docs/templates/extensions/adaptive/sprint-planning.patch.yaml)`
- `docs/templates/less_sprint_planning_template.md` → `docs/templates/core/sprint-planning/manifest.yaml (+ docs/templates/extensions/adaptive/sprint-planning.patch.yaml)`
- `docs/templates/pi_planning_template.md` → `docs/templates/core/sprint-planning/manifest.yaml (+ docs/templates/extensions/safe/sprint-planning.patch.yaml)`
- `docs/templates/sprint-review-template.md` → `docs/templates/core/sprint-review/manifest.yaml (+ docs/templates/extensions/adaptive/sprint-review.patch.yaml)`
- `docs/templates/sprint-retrospective-template.md` → `docs/templates/core/sprint-retrospective/manifest.yaml (+ docs/templates/extensions/adaptive/sprint-retrospective.patch.yaml)`
- `docs/templates/product_backlog_template.md` → `docs/templates/core/product-backlog/manifest.yaml (+ docs/templates/extensions/adaptive/product-backlog.patch.yaml)`
- `docs/templates/overall_product_backlog_template.md` → `docs/templates/core/product-backlog/manifest.yaml (+ docs/templates/extensions/safe/product-backlog.patch.yaml)`
- `docs/templates/deployment-checklist.md` → `docs/templates/core/deployment-checklist/manifest.yaml`
- `docs/templates/deployment-checklist-template.md` → `docs/templates/core/deployment-checklist/manifest.yaml`
- `docs/templates/executive-dashboard.md` → `docs/templates/core/executive-dashboard/manifest.yaml (+ docs/templates/extensions/safe/executive-dashboard.patch.yaml)`
- `docs/templates/executive-dashboard-template.md` → `docs/templates/core/executive-dashboard/manifest.yaml (+ docs/templates/extensions/safe/executive-dashboard.patch.yaml)`
- `docs/templates/executive-dashboard-workbook.md` → `docs/templates/core/executive-dashboard/manifest.yaml (+ workbook rendering layer)`

All inbound documentation links were updated to point at canonical targets under `docs/templates/core/**`.