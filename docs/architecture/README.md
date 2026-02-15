# Architecture Documentation

## Purpose

Describe the architecture documentation set and link the narrative to the repo assets that implement it.

## What's inside

- [docs/architecture/adr](/docs/architecture/adr): Subdirectory containing adr assets for this area.
- [docs/architecture/diagrams](/docs/architecture/diagrams): Subdirectory containing diagrams assets for this area.
- [docs/architecture/agent-orchestration.md](/docs/architecture/agent-orchestration.md): Markdown documentation for this area.
- [docs/architecture/ai-architecture.md](/docs/architecture/ai-architecture.md): Markdown documentation for this area.
- [docs/architecture/connector-architecture.md](/docs/architecture/connector-architecture.md): Markdown documentation for this area.
- [docs/architecture/data-architecture.md](/docs/architecture/data-architecture.md): Markdown documentation for this area.
- [docs/architecture/deployment-architecture.md](/docs/architecture/deployment-architecture.md): Deployment topology and infrastructure concerns.
- [docs/architecture/logical-architecture.md](/docs/architecture/logical-architecture.md): Logical component layout and service topology.
- [docs/architecture/security-architecture.md](/docs/architecture/security-architecture.md): Security controls and compliance design.

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
- Missing diagrams: verify files exist under `docs/architecture/diagrams/` where referenced:
  - `c4-context.puml`, `c4-container.puml`, `c4-component.puml`
  - `service-topology.puml`, `deployment-overview.puml`
