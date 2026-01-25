from __future__ import annotations

import streamlit as st

from ppm.state import get_store
from ppm.session import sidebar_login
from ppm.agents.registry import list_agents, run_agent, route_intent, orchestrate
from ppm.utils import json_dumps

st.set_page_config(page_title="Agents", layout="wide")

store = get_store()
user = sidebar_login(store)

st.title("Agents")

col1, col2 = st.columns([2, 1])

with col2:
    st.subheader("Run an agent (stub)")
    agent_id = st.number_input("Agent id", min_value=1, max_value=25, value=4, step=1)
    entity_id = st.text_input("Entity id (required for most agents)", value="")
    inputs_text = st.text_area("Inputs (JSON)", value="{}", height=120)
    if st.button("Run agent", type="primary"):
        try:
            import json
            inputs = json.loads(inputs_text) if inputs_text.strip() else {}
            out = run_agent(store, agent_id=int(agent_id), actor=user.name, entity_id=entity_id.strip() or None, inputs=inputs)
            st.success("Agent run complete.")
            st.json(out)
        except Exception as e:
            st.error(str(e))

    st.divider()
    st.subheader("Intent router")
    q = st.text_area("Try a query", value="Show me Apollo’s schedule and flag any budget risks", height=80)
    if st.button("Route query"):
        st.json(route_intent(q))
    if st.button("Orchestrate query"):
        st.json(orchestrate(store, actor=user.name, query=q, focus_entity_id=entity_id.strip() or None))

with col1:
    st.subheader("Agent specifications (from docs → JSON)")
    agents = list_agents()
    st.caption("Loaded from `apps/web/data/agents.json` (generated from the agent markdown specs).")

    for a in agents:
        aid = a.get("id")
        title = a.get("title") or f"Agent {aid}"
        with st.expander(f"{aid}. {title}", expanded=False):
            sections = a.get("sections", [])
            for s in sections:
                st.markdown(f"**{s.get('heading')}**")
                content = s.get("content", [])
                if content:
                    st.markdown("\n".join([f"- {c}" for c in content[:25]]))
                    if len(content) > 25:
                        st.caption(f"(showing first 25 of {len(content)} lines)")
                st.markdown("---")
