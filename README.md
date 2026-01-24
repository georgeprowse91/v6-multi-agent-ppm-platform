# Multi-Agent PPM Platform — Agentic System Repository

This repository packages the provided solution ZIP into a GitHub-friendly structure commonly used for detailed agentic systems (specs, docs, integrations, and placeholders for implementation artifacts).

## Repository map

- `specs/agents/` — Agent specifications grouped by domain (core, portfolio, delivery, governance, platform, operations)
- `docs/` — Architecture, product, governance, operations, business, and research documentation
- `integrations/` — Integration specs and (future) connector/adapters
- `manifest/MANIFEST.csv` — SHA-256 checksums and source→destination mapping (verifies nothing was lost)
- `scripts/verify_manifest.py` — Verifies file checksums using the manifest
- `archive/` — The original ZIP kept for byte-for-byte preservation
- `apps/prototype/` — Runnable Streamlit prototype web app that reflects the full documented functionality
- `src/`, `prompts/`, `workflows/`, `configs/`, `tools/`, `tests/`, `examples/` — Conventional directories for an agentic system implementation (currently placeholders)

## Document index

See **INDEX.md** for clickable links to all files.

## Preservation notes

- Git preserves file contents and paths; it does not preserve all filesystem metadata (e.g., original modification timestamps across platforms).
- Office files (`.docx`, `.pptx`, `.xlsx`) are marked as binary via `.gitattributes` to avoid accidental transformations.
- The original ZIP is included under `archive/` if you need the original packaging/metadata.

## Publish to GitHub

```bash
git init
git add -A
git commit -m "Initial import"
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```


## GitHub preview-friendly docs

Most source documents are Office formats (`.docx`, `.pptx`, `.xlsx`) which GitHub typically does **not** render inline.
For convenient browsing and search directly in GitHub, this repo includes Markdown exports:

- `docs_markdown/` — auto-generated `.md` versions of all `.docx` files (originals remain unchanged elsewhere).

> Note: Markdown exports are best-effort conversions. For authoritative formatting (tables/diagrams), use the original Office files.

