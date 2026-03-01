# Product Documentation

> Navigation hub for all product documentation. Restructured on 2026-03-01 to eliminate duplication, remove misplaced technical content, and ensure each fact appears in exactly one document.

---

## Document Map

```
docs/product/
├── README.md                                  ← You are here
├── CHANGELOG.md                               ← Documentation change history
│
├── 01-product-definition/                     ← What we build and why
│   ├── product-strategy-and-scope.md          ← Vision, scope, value proposition, differentiators
│   ├── requirements-specification.md          ← Functional and non-functional requirements
│   ├── personas-and-ux-guidelines.md          ← User personas and UI/UX design standards
│   ├── user-journeys-and-stage-gates.md       ← Methodology flows and governance enforcement
│   └── templates-and-methodology-catalog.md   ← Template cross-reference by agent and methodology
│
├── 02-commercial/                             ← How we position and sell it
│   ├── market-and-problem-analysis.md         ← Market data, AI adoption research, competitive landscape
│   ├── packaging-and-pricing.md               ← Commercial tiers, pricing models, value metrics
│   ├── competitive-positioning.md             ← Competitor battlecards
│   ├── go-to-market-plan.md                   ← GTM execution, segments, channels, financials
│   └── sales-enablement.md                    ← Pitch frameworks, messaging, objection handling
│
└── 03-user-guides/                            ← How users operate it
    ├── README.md                              ← Guide index
    ├── web-console-walkthroughs.md            ← Onboarding tours and guided walkthroughs
    └── assistant-panel-guide.md               ← AI assistant prompt library and interaction patterns
```

---

## Quick Navigation by Audience

| I am... | Start here |
|---|---|
| New to the platform | [Product Strategy and Scope](01-product-definition/product-strategy-and-scope.md) |
| A product manager or BA | [Requirements Specification](01-product-definition/requirements-specification.md) |
| A UX designer | [Personas and UX Guidelines](01-product-definition/personas-and-ux-guidelines.md) |
| A sales or GTM lead | [Go-to-Market Plan](02-commercial/go-to-market-plan.md) |
| Evaluating competitors | [Competitive Positioning](02-commercial/competitive-positioning.md) |
| An end user or operator | [User Guides](03-user-guides/README.md) |

---

## Related Technical Documentation

Product docs focus on vision, requirements, positioning, and user guides. For technical depth, see:

| Topic | Location |
|---|---|
| System architecture (27 docs) | [docs/architecture/](../architecture/) |
| Agent specifications (25 agents) | [docs/agents/](../agents/) |
| Connector ecosystem (44 integrations) | [docs/connectors/](../connectors/) |
| API contracts and OpenAPI specs | [docs/api/](../api/) |
| Data model, quality, and lineage | [docs/data/](../data/) |
| Compliance controls and DPIA | [docs/compliance/](../compliance/) |
| Test strategy and dependency matrix | [docs/testing/](../testing/) |
| Methodology frameworks and templates | [docs/methodology/](../methodology/) |
| Operational runbooks (15 docs) | [docs/runbooks/](../runbooks/) |
| Production readiness and release process | [docs/production-readiness/](../production-readiness/) |
| Cross-cutting solution index | [docs/solution-index.md](../solution-index.md) |

---

## Document Governance

- **One source of truth per topic.** Each document has a distinct, non-overlapping purpose.
- **Owner field required.** Every document must have an Owner line in its header.
- **Review cycle.** Quarterly review recommended; compliance-related docs reviewed more frequently.
- **No duplication.** If content is needed in multiple contexts, link to the canonical source rather than copying it. Market data lives in `market-and-problem-analysis.md`. Agent details live in `docs/agents/`. Connector details live in `docs/connectors/`.
- **Adding new docs.** Before creating a new document, verify it does not overlap with an existing canonical document. Place it in the most appropriate numbered folder.
- **Deprecation process.** See [CHANGELOG.md](CHANGELOG.md) for the full migration history.
