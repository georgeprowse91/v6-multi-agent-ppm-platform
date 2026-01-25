from __future__ import annotations

import json
import streamlit as st

from ppm.state import get_store
from ppm.session import sidebar_login
from ppm.requirements import load_requirements
from ppm.ui import entity_create_form, entity_picker, show_entity, entity_edit_form
from ppm.agents.registry import run_agent

st.set_page_config(page_title="Business Case & Investment Analysis", layout="wide")

store = get_store()
user = sidebar_login(store)

st.title("Business Case & Investment Analysis")

# Requirements
payload = load_requirements()
domain_reqs = []
for d in payload.get("functional_domains", []):
    if d.get("title") == "2. Business Case & Investment Analysis":
        domain_reqs = d.get("requirements", [])
        break

with st.expander("Documented requirements for this domain", expanded=False):
    if not domain_reqs:
        st.info("No requirements found in requirements.json for this domain section title.")
    else:
        for i, r in enumerate(domain_reqs, start=1):
            st.markdown(f"**{i}.** {r}")

st.divider()

left, right = st.columns([1, 1])

with left:
    st.subheader("Create / select")
    created_id = entity_create_form(store, user=user, entity_type="business_case")
    st.markdown("#### Select existing")
    selected_id = entity_picker(store, user=user, entity_type="business_case", label="business_case record")
    if created_id:
        selected_id = created_id

with right:
    st.subheader("Details")
    if not selected_id:
        st.info("Create or select a record to view details and run the domain agent.")
    else:
        show_entity(store, user=user, entity_id=selected_id)
        st.divider()
        entity_edit_form(store, user=user, entity_id=selected_id)

        st.divider()
        st.subheader("Run domain agent (prototype stub)")
        st.caption("This uses the corresponding agent stub to generate artifacts/updates that reflect the PRD domain capabilities.")
        inputs_text = st.text_area("Agent inputs (JSON)", value="{}", height=120, key="inputs_5")
        if st.button("Run agent 5", type="primary"):
            try:
                inputs = json.loads(inputs_text) if inputs_text.strip() else {}
                out = run_agent(store, agent_id=5, actor=user.name, entity_id=selected_id, inputs=inputs)
                st.success("Agent run complete.")
                st.json(out)
            except Exception as e:
                st.error(str(e))

        with st.expander("Recent agent runs for this record", expanded=False):
            runs = store.list_agent_runs(limit=50, entity_id=selected_id)
            st.json(runs)
