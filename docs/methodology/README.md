# Methodology

> This hub describes the three project delivery methodologies supported by the platform — Predictive (Waterfall), Adaptive (Agile/Scrum), and Hybrid — and explains how they are implemented as data-driven, runtime-navigable configurations. All methodology content is under `docs/methodology/`, with legacy `waterfall` content consolidated into `predictive` and legacy `agile` content consolidated into `adaptive`.

## Contents

- [Overview](#overview) — How methodologies are structured, loaded at runtime, and navigated.
- [Predictive (Waterfall)](#predictive-waterfall) — Sequential, stage-gated delivery with eight phases from Demand Intake through Closure.
- [Adaptive (Agile/Scrum)](#adaptive-agilescrum) — Iterative delivery with a repeatable sprint cycle and nine stages through Continuous Improvement.
- [Hybrid](#hybrid) — Combined stage-gated and iterative approach with parallel governance control.

---

## Overview

> Source: [overview.md](./overview.md)

Methodologies are first-class, data-driven configurations stored under `docs/methodology/<id>/`. Each methodology directory contains:

- `map.yaml` — WBS-driven navigation tree. Each node includes a deterministic `id`, `wbs`, `title`, `type`, and `order`.
- `gates.yaml` (optional) — Stage-gate definitions with entry/exit criteria, required artifacts, and approvers.
- `README.md` — Short methodology description.

### Supported methodologies

| ID | Description |
|----|-------------|
| `predictive` | Predictive/Waterfall sequential delivery |
| `adaptive` | Adaptive/Agile iterative delivery |
| `hybrid` | Combined stage-gated and iterative delivery |

The legacy folder names `agile` and `waterfall` were consolidated into `adaptive` and `predictive` respectively. Use the canonical IDs going forward.

### Runtime usage

`apps/web/src/methodologies.py` discovers all `*/map.yaml` files, validates node schema, loads optional `gates.yaml`, and normalizes output into the frontend-consumable structure (`stages`, `activities`, `navigation_nodes`, `gates`). Legacy `adaptive`/`predictive` IDs are aliased for backward compatibility.

### Navigation model

| Methodology | Navigation pattern |
|-------------|-------------------|
| **Predictive** | Sequential phases 0.1 → 0.7 |
| **Adaptive** | Phases 0.1 → 0.9 with 0.5 typed as `cycle` (`repeatable: true`) |
| **Hybrid** | Phase 0.7 typed as `governance` with `parallel: true`; Gate 0/1/2/3/4 metadata across phases 0.3, 0.4, and 0.8 |

### Consolidation note

- Legacy `agile` content is now part of `docs/methodology/adaptive`.
- Legacy `waterfall` content is now part of `docs/methodology/predictive`.

### Validating internal links

```bash
python ops/scripts/check-links.py
```

---

## Predictive (Waterfall)

> Source: [predictive/README.md](./predictive/README.md)

Sequential, stage-gated methodology driven by WBS-based navigation and gate approvals.

The legacy `docs/methodology/waterfall` folder has been consolidated into `predictive`. Use this folder for all waterfall/predictive delivery guidance.

### Stages and Activities

The predictive methodology map (`docs/methodology/predictive/map.yaml`) covers eight sequential phases:

1. **Demand Intake & Triage** — Capture and qualify demand for project initiation.
2. **Portfolio Assessment & Prioritisation** — Confirm strategic fit, value, and sequencing.
3. **Initiation & Chartering** — Establish sponsorship, scope intent, and governance.
4. **Detailed Planning & Baseline Setup** — Build scope, schedule, cost, and risk baselines.
5. **Execution & Delivery Control** — Deliver scope while managing formal change control.
6. **Monitoring, Reporting & Assurance** — Manage performance, risks, and quality controls.
7. **Deployment & Operational Readiness** — Prepare handover and adoption readiness.
8. **Closure & Benefits Transition** — Complete closure and transition to benefits tracking.

For gate checkpoints, see [`docs/methodology/predictive/gates.yaml`](./predictive/gates.yaml).

---

## Adaptive (Agile/Scrum)

> Source: [adaptive/README.md](./adaptive/README.md)

Adaptive/iterative methodology with a repeatable iteration cycle at WBS 0.5.

The legacy `docs/methodology/agile` folder has been consolidated into `adaptive`. Use this folder for all agile/adaptive delivery guidance.

### Stages and Activities

The adaptive methodology map (`docs/methodology/adaptive/map.yaml`) covers nine stages:

1. **Demand Intake & Triage** — Capture demand, assess fit, and route to discovery.
2. **Portfolio Assessment & Prioritisation** — Rank value, feasibility, and funding.
3. **Adaptive Initiation (Mobilisation & Setup)** — Establish team, governance, and tooling.
4. **Product Discovery & Backlog Formation** — Shape epics and stories; define acceptance criteria.
5. **Iterative Delivery Cycle (Repeatable)** — Sprint planning, execution, review, and release readiness.
6. **Deployment, Adoption & Value Realisation** — Release, adoption, and benefits tracking.
7. **Governance, Risk, and Portfolio Control** — Ensure controls remain current.
8. **Transition, Handover & Closure** — Complete support handover and closure evidence.
9. **Continuous Improvement Loop** — Apply retrospective outcomes to future cycles.

Phase 0.5 (Iterative Delivery Cycle) is typed as `cycle` with `repeatable: true`, enabling the platform to present it as a recurring loop in the navigation model.

For gate checkpoints, see [`docs/methodology/adaptive/gates.yaml`](./adaptive/gates.yaml).

---

## Hybrid

> Source: [hybrid/README.md](./hybrid/README.md)

Hybrid stage-gated and iterative methodology with parallel governance control at WBS 0.7.

The Hybrid methodology combines the structured, phase-gated progression of the Predictive approach with the iterative sprint cycles of the Adaptive approach. Phase 0.7 is typed as `governance` with `parallel: true`, allowing governance activities to run concurrently with delivery execution rather than as a sequential gate.

Gate metadata (Gate 0 through Gate 4) is distributed across phases 0.3, 0.4, and 0.8, providing formal decision checkpoints at key transitions while preserving the flexibility of iterative delivery within phases.

For the full stage and gate configuration, see [`docs/methodology/hybrid/map.yaml`](./hybrid/map.yaml) and [`docs/methodology/hybrid/gates.yaml`](./hybrid/gates.yaml) (if present).
