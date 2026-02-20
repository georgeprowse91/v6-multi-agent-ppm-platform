# Product Documentation

> This is the navigation hub for all `docs/product` documentation, reorganised into a MECE (Mutually Exclusive, Collectively Exhaustive) structure on 2026-02-20.
> Each folder has one clear purpose with minimal duplication. Legacy files from the previous structure are retained with deprecation banners during the transition period.

---

## Documentation Taxonomy

```
docs/product/
├── README.md                          ← You are here (navigation hub)
├── CHANGELOG.md                       ← Documentation change history
│
├── 01-product-definition/             ← What we are building and why
│   ├── product-strategy-and-scope.md
│   ├── requirements-specification.md
│   ├── personas-and-ux-guidelines.md
│   ├── user-journeys-and-stage-gates.md
│   └── templates-and-methodology-catalog.md
│
├── 02-solution-design/                ← How we are building it
│   ├── platform-architecture-overview.md
│   ├── agent-system-design.md
│   ├── assistant-panel-design.md
│   └── connectors/
│       └── iot-connector-spec.md
│
├── 03-delivery-and-quality/           ← How we deliver and validate it
│   ├── implementation-and-change-plan.md
│   ├── acceptance-and-test-strategy.md
│   └── compliance-evidence-process.md
│
├── 04-commercial-and-positioning/     ← How we sell and position it
│   ├── market-and-problem-analysis.md
│   ├── packaging-and-pricing.md
│   ├── competitive-positioning.md
│   ├── go-to-market-plan.md
│   └── sales-messaging-and-collateral.md
│
└── 05-user-guides/                    ← How users operate it
    ├── README.md
    └── web-console-walkthroughs.md
```

---

## Quick Navigation by Audience

| I am... | Start here |
|---|---|
| New to the platform | [01-product-definition/product-strategy-and-scope.md](01-product-definition/product-strategy-and-scope.md) |
| A product manager or BA | [01-product-definition/requirements-specification.md](01-product-definition/requirements-specification.md) |
| A UX designer | [01-product-definition/personas-and-ux-guidelines.md](01-product-definition/personas-and-ux-guidelines.md) |
| A solution architect | [02-solution-design/platform-architecture-overview.md](02-solution-design/platform-architecture-overview.md) |
| An AI/ML engineer | [02-solution-design/agent-system-design.md](02-solution-design/agent-system-design.md) |
| An integration engineer | [02-solution-design/connectors/iot-connector-spec.md](02-solution-design/connectors/iot-connector-spec.md) |
| A delivery manager | [03-delivery-and-quality/implementation-and-change-plan.md](03-delivery-and-quality/implementation-and-change-plan.md) |
| A QA/test engineer | [03-delivery-and-quality/acceptance-and-test-strategy.md](03-delivery-and-quality/acceptance-and-test-strategy.md) |
| A compliance or audit lead | [03-delivery-and-quality/compliance-evidence-process.md](03-delivery-and-quality/compliance-evidence-process.md) |
| A sales or GTM lead | [04-commercial-and-positioning/go-to-market-plan.md](04-commercial-and-positioning/go-to-market-plan.md) |
| Evaluating competitors | [04-commercial-and-positioning/competitive-positioning.md](04-commercial-and-positioning/competitive-positioning.md) |
| An end user or operator | [05-user-guides/README.md](05-user-guides/README.md) |

---

## Previous Structure (Legacy Navigation)

The following files from the pre-migration structure are retained with deprecation banners during the transition period. They will be removed after one release cycle. Use the table above for all new references.

| Legacy file | Migrated to |
|---|---|
| `solution-overview.md` | [01-product-definition/product-strategy-and-scope.md](01-product-definition/product-strategy-and-scope.md) |
| `solution-overview/README.md` | [01-product-definition/product-strategy-and-scope.md](01-product-definition/product-strategy-and-scope.md) |
| `product-requirements.md` | [01-product-definition/requirements-specification.md](01-product-definition/requirements-specification.md) |
| `personas.md` | [01-product-definition/personas-and-ux-guidelines.md](01-product-definition/personas-and-ux-guidelines.md) |
| `user-journeys.md` | [01-product-definition/user-journeys-and-stage-gates.md](01-product-definition/user-journeys-and-stage-gates.md) |
| `templates-catalog.md` | [01-product-definition/templates-and-methodology-catalog.md](01-product-definition/templates-and-methodology-catalog.md) |
| `solution-overview/platform-overview.md` | [02-solution-design/platform-architecture-overview.md](02-solution-design/platform-architecture-overview.md) |
| `solution-overview/agents/agent-01-*.md` … `agent-25-*.md` | [02-solution-design/agent-system-design.md](02-solution-design/agent-system-design.md) |
| `assistant-panel.md` | [02-solution-design/assistant-panel-design.md](02-solution-design/assistant-panel-design.md) |
| `connectors/iot.md` | [02-solution-design/connectors/iot-connector-spec.md](02-solution-design/connectors/iot-connector-spec.md) |
| `success-metrics.md` | [03-delivery-and-quality/implementation-and-change-plan.md](03-delivery-and-quality/implementation-and-change-plan.md) |
| `solution-overview/change-management-training.md` | [03-delivery-and-quality/implementation-and-change-plan.md](03-delivery-and-quality/implementation-and-change-plan.md) |
| `acceptance-criteria.md` | [03-delivery-and-quality/acceptance-and-test-strategy.md](03-delivery-and-quality/acceptance-and-test-strategy.md) |
| `user-guides/certification-evidence.md` | [03-delivery-and-quality/compliance-evidence-process.md](03-delivery-and-quality/compliance-evidence-process.md) |
| `solution-overview/market-analysis.md` | [04-commercial-and-positioning/market-and-problem-analysis.md](04-commercial-and-positioning/market-and-problem-analysis.md) |
| `solution-overview/research-whitepaper.md` | [04-commercial-and-positioning/market-and-problem-analysis.md](04-commercial-and-positioning/market-and-problem-analysis.md) |
| `solution-overview/pricing-packaging.md` | [04-commercial-and-positioning/packaging-and-pricing.md](04-commercial-and-positioning/packaging-and-pricing.md) |
| `solution-overview/competitive-battlecards.md` | [04-commercial-and-positioning/competitive-positioning.md](04-commercial-and-positioning/competitive-positioning.md) |
| `solution-overview/go-to-market-strategy.md` | [04-commercial-and-positioning/go-to-market-plan.md](04-commercial-and-positioning/go-to-market-plan.md) |
| `solution-overview/pitch-overview.md` | [04-commercial-and-positioning/sales-messaging-and-collateral.md](04-commercial-and-positioning/sales-messaging-and-collateral.md) |
| `solution-overview/sales-enablement.md` | [04-commercial-and-positioning/sales-messaging-and-collateral.md](04-commercial-and-positioning/sales-messaging-and-collateral.md) |
| `solution-overview/marketing-sales-collateral.md` | [04-commercial-and-positioning/sales-messaging-and-collateral.md](04-commercial-and-positioning/sales-messaging-and-collateral.md) |
| `user-guides/README.md` | [05-user-guides/README.md](05-user-guides/README.md) |
| `user-guides/web-console-walkthroughs.md` | [05-user-guides/web-console-walkthroughs.md](05-user-guides/web-console-walkthroughs.md) |

---

## Document Governance

- **One source of truth per topic.** Each document has a distinct, non-overlapping purpose.
- **Owner field required.** Every document must have an Owner line in its header.
- **Review cycle.** Quarterly review recommended; compliance-related docs reviewed more frequently.
- **Adding new docs.** Before creating a new document, verify it does not overlap with an existing canonical document. Place it in the most appropriate numbered folder.
- **Deprecation process.** See `CHANGELOG.md` for the deprecation timeline of legacy files.
