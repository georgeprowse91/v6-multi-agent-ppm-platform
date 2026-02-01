# Solution Overview Documentation

## Purpose

Describe the solution overview documentation set and link the narrative to the repo assets that implement it. Recent additions include connector certification evidence tracking and guided UI walkthroughs for the web console.

## Implementation alignment

The files in this folder are go-to-market narratives. The repository already includes the core execution stack (API gateway, orchestration service, workflow engine, agent runtime, connector registry, data sync service, analytics service, and data-lineage service) plus a web console (`apps/web`) with the workspace shell, dashboard canvas, connector gallery, guided tours, and assistant panel. Certification evidence tracking now lives alongside connector management to close compliance gaps. Use the Solution Index to cross-reference deeper architecture details and the latest runtime configuration.

## What's inside

- `docs/product/solution-overview/change-management-training.md`: Markdown documentation for this area.
- `docs/product/solution-overview/competitive-battlecards.md`: Markdown documentation for this area.
- `docs/product/solution-overview/go-to-market-strategy.md`: Markdown documentation for this area.
- `docs/product/solution-overview/market-analysis.md`: Markdown documentation for this area.
- `docs/product/solution-overview/marketing-sales-collateral.md`: Markdown documentation for this area.
- `docs/product/solution-overview/platform-overview.md`: Markdown documentation for this area.

## How it's used

These documents are referenced by the root README and provide the canonical explanations for the platform architecture, data model, and operating procedures.

## How to run / develop / test

Validate internal links across docs:

```bash
python scripts/check-links.py
```

## Configuration

No configuration. Documentation content lives in Markdown and YAML files under this folder.

## Troubleshooting

- Broken links: run the link checker and fix any relative path mismatches.
- Missing diagrams: verify files exist under `docs/architecture/diagrams/` where referenced.
