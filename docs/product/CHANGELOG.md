# Product Documentation Changelog

All notable changes to product documentation will be documented in this file.

---

## [2026-03-01] — Deduplication and Restructure

### Summary

Reorganised `docs/product/` from 21 files across 5 folders to 13 files across 3 folders. Eliminated cross-document repetition, moved misplaced technical content to its canonical home, reconciled conflicting market statistics, and updated all documents to reflect verified codebase facts.

### Structural Changes

The previous five-folder taxonomy has been reduced to three folders:

```
01-product-definition/   — What we build and why (unchanged)
02-commercial/           — How we position and sell it (renamed from 04-commercial-and-positioning)
03-user-guides/          — How users operate it (renamed from 05-user-guides)
```

The `02-solution-design/` and `03-delivery-and-quality/` folders have been removed. Their content has been moved to the canonical technical documentation folders where it belongs.

### Files Moved Out of docs/product/

| Former location | New canonical location | Reason |
|---|---|---|
| `02-solution-design/agent-system-design.md` | [docs/agents/agent-specifications.md](../agents/agent-specifications.md) | Agent specs belong with agent documentation |
| `02-solution-design/connectors/iot-connector-spec.md` | [docs/connectors/iot-connector-spec.md](../connectors/iot-connector-spec.md) | Connector specs belong with connector documentation |
| `03-delivery-and-quality/acceptance-and-test-strategy.md` | [docs/testing/acceptance-and-test-strategy.md](../testing/acceptance-and-test-strategy.md) | Test strategy belongs with test documentation |
| `03-delivery-and-quality/compliance-evidence-process.md` | [docs/compliance/certification-evidence-process.md](../compliance/certification-evidence-process.md) | Compliance processes belong with compliance documentation |
| `03-delivery-and-quality/implementation-and-change-plan.md` | [docs/change-management/implementation-and-change-plan.md](../change-management/implementation-and-change-plan.md) | Delivery/change management content |

### Files Removed

| File | Reason |
|---|---|
| `02-solution-design/platform-architecture-overview.md` | Duplicated by 27 files in [docs/architecture/](../architecture/) |
| `02-solution-design/assistant-panel-design.md` | User-facing parts moved to `03-user-guides/assistant-panel-guide.md`; technical details covered by [docs/architecture/](../architecture/) |
| `04-commercial-and-positioning/sales-messaging-and-collateral.md` | Replaced by slimmer `02-commercial/sales-enablement.md` with duplication removed |

### New Files

| File | Purpose |
|---|---|
| `02-commercial/sales-enablement.md` | Sales-specific messaging, pitch frameworks, and collateral index (replaces sales-messaging-and-collateral.md) |
| `03-user-guides/assistant-panel-guide.md` | User-facing guide for the AI assistant panel and prompt library |

### Deduplication Changes

- **Problem statement and value proposition**: Now appears only in `product-strategy-and-scope.md`. Removed from sales-messaging, go-to-market, and other documents; they link to the strategy doc instead.
- **Agent descriptions**: Removed from product docs entirely. All documents reference [docs/agents/](../agents/) for agent details.
- **Connector ecosystem**: Removed detailed listings. All documents reference [docs/connectors/](../connectors/) for connector details.
- **Market statistics**: Now appear only in `market-and-problem-analysis.md` with a reconciliation table showing multiple analyst sources. Removed from packaging-and-pricing, go-to-market, and requirements docs.
- **Methodology-as-navigation**: Conceptual explanation appears only in `product-strategy-and-scope.md`. Operational detail in `user-journeys-and-stage-gates.md`. Other docs link to these.

### Codebase Accuracy Updates

- Verified connector count: 38 connectors (10 production-ready) per capability matrix (authoritative source: `docs/connectors/generated/capability-matrix.md`)
- Verified 25 agents across 4 groups (core orchestration, delivery, operations, portfolio)
- Verified tech stack: React 18, TypeScript 5.3, FastAPI 0.115+, PostgreSQL 15, Redis 7

---

## [Unreleased] (prior to 2026-03-01)

### Added
- Methodology-specific roles and responsibilities templates for Predictive, Adaptive, and Hybrid projects.

### Removed
- Deprecated pre-migration files in `docs/product` that were previously retained with deprecation banners.

---

## [2026-02-20] — MECE Restructure Migration

### Summary

Complete reorganisation of `docs/product` into a MECE (Mutually Exclusive, Collectively Exhaustive) five-folder taxonomy. Each document now has a single canonical location and clear ownership. Legacy files are retained with deprecation banners during the transition period.

### New Structure (superseded by 2026-03-01 restructure)

```
docs/product/
├── 01-product-definition/   — What we build and why
├── 02-solution-design/      — How we build it (removed 2026-03-01)
├── 03-delivery-and-quality/ — How we deliver and validate it (removed 2026-03-01)
├── 04-commercial-and-positioning/ — How we sell and position it (renamed to 02-commercial)
└── 05-user-guides/          — How users operate it (renamed to 03-user-guides)
```

### Governance

- All new authoring must happen in the three-folder canonical structure.
- After one release cycle, open a PR to delete all deprecated files listed above.
