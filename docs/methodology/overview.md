# Methodology Overview

Methodologies are first-class, data-driven configs under `docs/methodology/<id>/`.

## Supported methodologies

- `predictive` (Predictive/Predictive)
- `adaptive` (Adaptive/Adaptive)
- `hybrid`

## Files per methodology

Legacy folders `agile` and `waterfall` were consolidated into `adaptive` and `predictive` respectively; use those canonical IDs going forward.

- `map.yaml`: WBS-driven navigation tree. Each node includes deterministic `id`, `wbs`, `title`, `type`, and `order`.
- `gates.yaml` (optional): stage-gate definitions with entry/exit criteria, required artifacts, and approvers.
- `README.md`: short methodology description.

## Runtime usage

`apps/web/src/methodologies.py` discovers all `*/map.yaml` files, validates node schema, loads optional `gates.yaml`, and normalizes output into the frontend-consumable structure (`stages`, `activities`, `navigation_nodes`, `gates`).

Legacy `adaptive`/`predictive` IDs are aliased to `adaptive`/`predictive` for compatibility.

## Navigation model

- **Predictive**: sequential phases 0.1 → 0.7.
- **Adaptive**: phases 0.1 → 0.9 with 0.5 typed as `cycle` (`repeatable: true`).
- **Hybrid**: 0.7 typed as `governance` with `parallel: true`, with Gate 0/1/2/3/4 metadata across 0.3, 0.4, and 0.8.
