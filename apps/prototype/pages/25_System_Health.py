from __future__ import annotations

import streamlit as st

from ppm.state import get_store
from ppm.session import sidebar_login
from ppm.agents.registry import run_agent

st.set_page_config(page_title="System Health & Monitoring", layout="wide")

store = get_store()
user = sidebar_login(store)

st.title("System Health & Monitoring")

st.markdown(
    """This page prototypes **observability**, **system health checks**, and basic **metrics/event views**.

In production, this would integrate with monitoring/alerting stacks, SLOs/SLAs, and distributed tracing.

In the prototype, we derive health from the local DB state and recent events/metrics."""
)

if st.button("Run health check (Agent 25)", type="primary"):
    try:
        out = run_agent(store, agent_id=25, actor=user.name, entity_id=None, inputs={})
        st.success(f"Status: {out.get('status')}")
        st.json(out)
    except Exception as e:
        st.error(str(e))

st.divider()
st.subheader("Latest metrics")
st.json(store.latest_metrics(limit=50))

st.divider()
st.subheader("Recent events")
st.json(store.list_events(limit=50))

st.divider()
st.subheader("Recent agent runs")
st.json(store.list_agent_runs(limit=50))
