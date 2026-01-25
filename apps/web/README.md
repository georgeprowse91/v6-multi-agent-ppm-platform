# Prototype Web App

This prototype is a **web UI** you can run locally to explore the Multi‑Agent PPM Platform as described in the included documentation.

It is designed to **reflect the full functional scope** in the Product Requirements document and the 25 Agent Specifications by:

- Providing a dedicated page for each functional domain
- Implementing lightweight CRUD for the major PPM objects (intakes, business cases, portfolios, programs, projects, risks, etc.)
- Including runnable **agent stubs** that generate artifacts (charter, business case, schedule plan, risk register, compliance mapping, comms plan, etc.)
- Including a simple **workflow engine** with **approval gates**
- Recording **audit events** and basic **system health metrics**

> Note: This is prototype-grade (not production-grade). The goal is accurate coverage and traceability to the documented functionality.

## Run locally

```bash
cd apps/web
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## What you will see

- **Overview**: capability map, key workflows, architecture notes
- **Requirements**: the functional/non-functional requirements are loaded from `data/requirements.json` (generated from the PRD markdown)
- **Agents**: all 25 agents with their capability text (loaded from `data/agents.json` generated from the agent markdown specs)
- **Domain pages**: create/update objects and run the domain agent
- **Workflows**: start workflow instances (e.g., intake → delivery setup), progress steps, and pass/fail gates
- **Docs viewer**: search and read text extracted from repository DOCX specifications (where present)

## Data storage

- A local SQLite database is created at `apps/web/data/ppm.db`.
- All objects are stored as JSON payloads in an entity store to keep the prototype flexible while still covering all domains.

## Login / roles

There is no real authentication in the prototype.

- Use the sidebar **“Login”** selector to switch between example personas/roles.
- Role-based and data-classification checks are simulated to reflect the PRD’s RBAC / data-level security requirements.

## Regenerating prototype metadata from Markdown

The JSON files in `apps/web/data/` are derived from the source documents:

- `requirements.json` ← Product Requirements markdown
- `agents.json` ← Agent Specs markdown

If you update the docs, you can re-run `apps/web/scripts/generate_metadata.py` to regenerate these files.
