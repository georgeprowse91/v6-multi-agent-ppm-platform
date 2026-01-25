# Prototype Web App

Streamlit-based prototype UI for exploring the platform's domain coverage and agent stubs.

## Current state

- Prototype UI is implemented in `apps/web/streamlit_app.py` with domain pages under
  `apps/web/pages/`.
- Data is stored locally in SQLite at `apps/web/data/ppm.db` when you run the app.
- Agent behavior is stubbed but wired to produce artifacts for demo workflows.

## Quickstart

```bash
make run-prototype
```

If you prefer a virtual environment:

```bash
cd apps/web
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## How to verify

Open the UI at:

- http://localhost:8501

You should see the "Multi-Agent PPM Platform — Prototype Web App" title and navigation
for domain pages.

## Key files

- `apps/web/streamlit_app.py`: main Streamlit entrypoint.
- `apps/web/pages/`: domain-specific UI pages.
- `apps/web/ppm/agents/stubs.py`: agent stub implementations.
- `apps/web/scripts/generate_metadata.py`: regenerates JSON metadata from docs.

## Example

Regenerate prototype metadata from docs:

```bash
python apps/web/scripts/generate_metadata.py
```

Expected output:

```text
Wrote apps/web/data/requirements.json
Wrote apps/web/data/agents.json
```

## Next steps

- Replace stub agent logic in `apps/web/ppm/agents/stubs.py` with real service calls.
- Add persistence beyond local SQLite by wiring to `services/` data stores.
