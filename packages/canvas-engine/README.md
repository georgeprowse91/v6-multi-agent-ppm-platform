# Canvas Engine Package

Planned package for generating visual canvases used in portfolio and program views.

## Current state

- No implementation code yet in `packages/canvas-engine/`.
- Prototype UI renders visual elements via Streamlit in `apps/web/`.

## Quickstart

Open the prototype UI:

```bash
make run-prototype
```

## How to verify

Navigate to the "Portfolio" page in the UI to see current visual summaries.

## Key files

- `apps/web/pages/06_Portfolio.py`: prototype portfolio page.
- `packages/canvas-engine/README.md`: scope and next steps.

## Example

Open the portfolio page source:

```bash
sed -n '1,120p' apps/web/pages/06_Portfolio.py
```

## Next steps

- Implement visualization helpers under `packages/canvas-engine/src/`.
- Replace Streamlit-specific rendering with reusable components.
