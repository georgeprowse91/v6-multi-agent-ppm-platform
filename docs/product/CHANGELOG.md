# Product Documentation Changelog

All notable changes to product documentation will be documented in this file.

---

## [Unreleased]

### Added
- Methodology-specific roles & responsibilities templates for Predictive, Adaptive, and Hybrid projects.

### Removed
- Deprecated pre-migration files in `docs/product` that were previously retained with deprecation banners (legacy `solution-overview*`, top-level legacy docs, and old `user-guides`/`connectors` paths).

---

## [2026-02-20] — MECE Restructure Migration

### Summary

Complete reorganisation of `docs/product` into a MECE (Mutually Exclusive, Collectively Exhaustive) five-folder taxonomy. Each document now has a single canonical location and clear ownership. Legacy files are retained with deprecation banners during the transition period (removal after one release cycle).

### New Structure

```
docs/product/
├── 01-product-definition/   — What we build and why
├── 02-solution-design/      — How we build it
├── 03-delivery-and-quality/ — How we deliver and validate it
├── 04-commercial-and-positioning/ — How we sell and position it
└── 05-user-guides/          — How users operate it
```

### New Files Added

| New canonical file | Migration action |
|---|---|
| `01-product-definition/product-strategy-and-scope.md` | Consolidated from `solution-overview.md`, `solution-overview/README.md`, and strategic sections of `solution-overview/pitch-overview.md` |
| `01-product-definition/requirements-specification.md` | Lifted and shifted from `product-requirements.md` |
| `01-product-definition/personas-and-ux-guidelines.md` | Lifted and shifted from `personas.md` |
| `01-product-definition/user-journeys-and-stage-gates.md` | Lifted and shifted from `user-journeys.md` |
| `01-product-definition/templates-and-methodology-catalog.md` | Lifted and shifted from `templates-catalog.md` |
| `02-solution-design/platform-architecture-overview.md` | Lifted and shifted from `solution-overview/platform-overview.md` |
| `02-solution-design/agent-system-design.md` | Consolidated all 25 `solution-overview/agents/agent-*.md` files into one canonical catalog |
| `02-solution-design/assistant-panel-design.md` | Moved from `assistant-panel.md` |
| `02-solution-design/connectors/iot-connector-spec.md` | Renamed and moved from `connectors/iot.md` |
| `03-delivery-and-quality/implementation-and-change-plan.md` | Merged from `success-metrics.md` and `solution-overview/change-management-training.md` |
| `03-delivery-and-quality/acceptance-and-test-strategy.md` | Lifted and shifted from `acceptance-criteria.md` |
| `03-delivery-and-quality/compliance-evidence-process.md` | Moved from `user-guides/certification-evidence.md` |
| `04-commercial-and-positioning/market-and-problem-analysis.md` | Consolidated from `solution-overview/market-analysis.md` and `solution-overview/research-whitepaper.md` |
| `04-commercial-and-positioning/packaging-and-pricing.md` | Moved from `solution-overview/pricing-packaging.md` |
| `04-commercial-and-positioning/competitive-positioning.md` | Moved from `solution-overview/competitive-battlecards.md` |
| `04-commercial-and-positioning/go-to-market-plan.md` | Moved from `solution-overview/go-to-market-strategy.md` |
| `04-commercial-and-positioning/sales-messaging-and-collateral.md` | Consolidated from `solution-overview/pitch-overview.md`, `solution-overview/sales-enablement.md`, and `solution-overview/marketing-sales-collateral.md` |
| `05-user-guides/README.md` | Updated from `user-guides/README.md` |
| `05-user-guides/web-console-walkthroughs.md` | Moved from `user-guides/web-console-walkthroughs.md` |

### Deprecated Files (Retained with Banners — Pending Removal)

The following legacy files are retained during the transition period with deprecation banners pointing to their new canonical locations. They will be removed after one release cycle.

| Deprecated file | Redirects to |
|---|---|
| `solution-overview.md` | `01-product-definition/product-strategy-and-scope.md` |
| `solution-overview/README.md` | `01-product-definition/product-strategy-and-scope.md` |
| `product-requirements.md` | `01-product-definition/requirements-specification.md` |
| `personas.md` | `01-product-definition/personas-and-ux-guidelines.md` |
| `user-journeys.md` | `01-product-definition/user-journeys-and-stage-gates.md` |
| `templates-catalog.md` | `01-product-definition/templates-and-methodology-catalog.md` |
| `solution-overview/platform-overview.md` | `02-solution-design/platform-architecture-overview.md` |
| `solution-overview/agents/intent-router-agent-*.md` … `system-health-agent-*.md` | `02-solution-design/agent-system-design.md` |
| `assistant-panel.md` | `02-solution-design/assistant-panel-design.md` |
| `connectors/iot.md` | `02-solution-design/connectors/iot-connector-spec.md` |
| `success-metrics.md` | `03-delivery-and-quality/implementation-and-change-plan.md` |
| `solution-overview/change-management-training.md` | `03-delivery-and-quality/implementation-and-change-plan.md` |
| `acceptance-criteria.md` | `03-delivery-and-quality/acceptance-and-test-strategy.md` |
| `user-guides/certification-evidence.md` | `03-delivery-and-quality/compliance-evidence-process.md` |
| `solution-overview/market-analysis.md` | `04-commercial-and-positioning/market-and-problem-analysis.md` |
| `solution-overview/research-whitepaper.md` | `04-commercial-and-positioning/market-and-problem-analysis.md` |
| `solution-overview/pricing-packaging.md` | `04-commercial-and-positioning/packaging-and-pricing.md` |
| `solution-overview/competitive-battlecards.md` | `04-commercial-and-positioning/competitive-positioning.md` |
| `solution-overview/go-to-market-strategy.md` | `04-commercial-and-positioning/go-to-market-plan.md` |
| `solution-overview/pitch-overview.md` | `04-commercial-and-positioning/sales-messaging-and-collateral.md` |
| `solution-overview/sales-enablement.md` | `04-commercial-and-positioning/sales-messaging-and-collateral.md` |
| `solution-overview/marketing-sales-collateral.md` | `04-commercial-and-positioning/sales-messaging-and-collateral.md` |
| `user-guides/README.md` | `05-user-guides/README.md` |
| `user-guides/web-console-walkthroughs.md` | `05-user-guides/web-console-walkthroughs.md` |

### Governance

- All new authoring must happen in the five-folder canonical structure.
- Legacy files must NOT be edited; update only their canonical counterparts.
- After one release cycle, open a PR to delete all deprecated files listed above.
