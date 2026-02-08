# Template Library

## Purpose
Provide reusable templates that are organized by discipline and usable across predictive,
agile, and hybrid delivery practices.

## What's inside
Templates are grouped by discipline. Each discipline directory contains formats such as plans,
reports, checklists, registers, and matrices. File names include the format and methodology
variant so it is easy to find a specific template.

### Disciplines
- `change/`: Change management plans, requests, logs, and readiness artefacts.
- `communications/`: Communication plans, calendars, meeting guides, and stakeholder comms.
- `finance/`: Budgets, cost/ROI artefacts, procurement, and vendor management.
- `governance/`: Governance frameworks, decision models, charters, and escalation artefacts.
- `portfolio-program/`: Portfolio/program business cases, benefits, prioritization, and roadmaps.
- `product/`: Product strategy, vision, backlog, and agile delivery templates.
- `quality/`: Quality plans, checklists, assessments, and UAT materials.
- `requirements/`: Scope, requirements libraries, traceability, and analysis artefacts.
- `resources/`: Resource planning, team performance, and roles/responsibilities.
- `risk/`: Risk registers, issue/assumption logs, and risk analysis tools.
- `schedule/`: Schedules, WBS, milestones, and release planning.
- `stakeholders/`: Stakeholder analysis, mapping, and engagement tools.

## Naming convention
Templates follow the pattern:

```
<template-name>-<format>-<methodology>
```

Examples:
- `change-request-request-cross.md`
- `sprint-plan-plan-agile.md`
- `project-charter-charter-waterfall.md`

Use `cross` for templates applicable across methodologies. If multiple variants of the same
template exist, the filename includes `-var1`, `-var2`, etc.

## How it's used
Templates are referenced by methodology maps and the template catalog. Tailor sections by
adding or removing rows, adapting terminology, and mapping artefacts to local governance
expectations.

## Spreadsheet Templates
Some templates are delivered as spreadsheets (e.g., cost baseline, risk register). Use Excel or
Google Sheets to edit these files and preserve formulas. If your workflow requires an online
version, upload the spreadsheet to your document repository and link it from the catalog.

## Related References
- Template catalog (`docs/product/templates-catalog.md`).
