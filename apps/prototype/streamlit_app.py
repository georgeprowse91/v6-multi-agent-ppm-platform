from __future__ import annotations

import streamlit as st

from ppm.state import get_store
from ppm.session import sidebar_login
from ppm.agents.registry import route_intent, orchestrate, run_agent
from ppm.workflows.engine import start_workflow
from ppm.ui import entity_create_form

st.set_page_config(page_title="Agentic PPM Platform Prototype", layout="wide")

store = get_store()
user = sidebar_login(store)

# -----------------------------
# Sidebar assistant
# -----------------------------
st.sidebar.divider()
st.sidebar.subheader("Ask the PPM assistant")
query = st.sidebar.text_area(
    "Natural language request",
    value="",
    height=80,
    placeholder="e.g., Show me Apollo’s schedule and flag any budget risks",
)
focus_entity = st.sidebar.text_input("Focus entity id (optional)", value="")

colA, colB = st.sidebar.columns(2)
with colA:
    if st.button("Route", use_container_width=True):
        st.sidebar.json(route_intent(query))
with colB:
    if st.button("Orchestrate", use_container_width=True):
        r = orchestrate(store, actor=user.name, query=query, focus_entity_id=focus_entity or None)
        st.sidebar.json(r)
        # Optional: auto-run the suggested agent (single-agent orchestration in prototype)
        for a in r.get("actions", []):
            if a.get("type") == "run_agent":
                try:
                    out = run_agent(
                        store,
                        agent_id=int(a["agent_id"]),
                        actor=user.name,
                        entity_id=a.get("entity_id"),
                        inputs={},
                    )
                    st.sidebar.success(f"Ran agent {a['agent_id']}")
                    st.sidebar.json(out)
                except Exception as e:
                    st.sidebar.error(str(e))

# -----------------------------
# Main
# -----------------------------
st.title("Multi‑Agent PPM Platform — Prototype Web App")

st.markdown(
    """This prototype provides an explorable UI for the **full functional scope** described in the solution documents.

Use the left navigation (Streamlit pages) to explore domains, agents, workflows, integrations, analytics, and system health."""
)

# KPI tiles
projects = store.list_entities(type="project", limit=500)
intakes = store.list_entities(type="intake", limit=500)
business_cases = store.list_entities(type="business_case", limit=500)
risks = store.list_entities(type="risk", limit=500)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Intake requests", len(intakes))
c2.metric("Business cases", len(business_cases))
c3.metric("Projects", len(projects))
c4.metric("Risks", len(risks))

st.divider()
st.subheader("Quick start")

left, right = st.columns([1, 1])

with left:
    st.markdown("#### Create an intake")
    created = entity_create_form(store, user=user, entity_type="intake", default_title="New initiative")
    if created:
        st.success(f"Intake created: {created}")

with right:
    st.markdown("#### Start the intake → delivery setup workflow")
    defs = store.list_workflow_defs()
    wf_opts = {f"{d['name']} ({d['id']})": d["id"] for d in defs if d.get("active") == 1}
    chosen = st.selectbox("Workflow", list(wf_opts.keys())) if wf_opts else None
    target_entity = st.text_input("Entity id (attach workflow to)", placeholder="Paste an intake id here")
    if st.button("Start workflow", type="primary"):
        if not chosen:
            st.error("No workflow definitions found.")
        elif not target_entity.strip():
            st.error("Provide an entity id.")
        else:
            try:
                instance_id = start_workflow(store, def_id=wf_opts[chosen], entity_id=target_entity.strip(), actor=user.name)
                st.success(f"Workflow started: {instance_id}")
            except Exception as e:
                st.error(str(e))

st.divider()
st.subheader("Recent activity")
events = store.list_events(limit=15)
if events:
    st.json(events)
else:
    st.info("No events yet.")
