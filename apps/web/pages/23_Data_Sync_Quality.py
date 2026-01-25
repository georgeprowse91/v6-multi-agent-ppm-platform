from __future__ import annotations

import json

import streamlit as st
from ppm.agents.registry import run_agent
from ppm.session import sidebar_login
from ppm.state import get_store
from ppm.utils import json_dumps

st.set_page_config(page_title="Data Synchronisation & Quality", layout="wide")

store = get_store()
user = sidebar_login(store)

st.title("Data Synchronisation & Quality")

st.markdown(
    """This page prototypes the **connector registry** and **sync execution** described in the solution documents.

In production, these connectors would call vendor APIs (Jira/Azure DevOps, Workday, SAP, Oracle, Teams/Slack, etc.) with retries, pagination, and standardised error handling.

In the prototype, sync updates `last_sync`, records events, and emits metrics."""
)

st.divider()
st.subheader("Connector registry (simulated)")

connectors = store.list_connectors()
if not connectors:
    st.info("No connectors found. Seed data should add a few (Jira, Teams, Workday, SAP).")
else:
    for c in connectors:
        with st.expander(
            f"{c['system_name']} · {c.get('status')} · last_sync={c.get('last_sync')}",
            expanded=False,
        ):
            st.caption(f"id={c['id']} · category={c.get('category')}")
            status = st.selectbox(
                "Status",
                options=["Planned", "Configured", "Paused", "Error"],
                index=["Planned", "Configured", "Paused", "Error"].index(
                    c.get("status") or "Planned"
                ),
                key=f"status_{c['id']}",
            )
            category = st.text_input(
                "Category", value=c.get("category") or "", key=f"cat_{c['id']}"
            )
            cfg_text = st.text_area(
                "Config JSON",
                value=json_dumps(c.get("config") or {}),
                height=200,
                key=f"cfg_{c['id']}",
            )
            if st.button("Save connector", key=f"save_{c['id']}"):
                try:
                    cfg = json.loads(cfg_text) if cfg_text.strip() else {}
                    store.upsert_connector(
                        connector_id=c["id"],
                        system_name=c["system_name"],
                        category=category or None,
                        status=status,
                        config=cfg,
                        last_sync=c.get("last_sync"),
                    )
                    store.log_event(
                        actor=user.name,
                        event_type="connector_updated",
                        entity_id=None,
                        details={"connector_id": c["id"], "system": c["system_name"]},
                    )
                    st.success("Saved.")
                except Exception as e:
                    st.error(str(e))

st.divider()
st.subheader("Run sync")

only = st.multiselect(
    "Sync only these systems (optional)",
    options=[c["system_name"] for c in connectors] if connectors else [],
)
if st.button("Run connector sync (agent 23)", type="primary"):
    try:
        out = run_agent(
            store,
            agent_id=23,
            actor=user.name,
            entity_id=None,
            inputs={"only": only} if only else {},
        )
        st.success("Sync complete.")
        st.json(out)
    except Exception as e:
        st.error(str(e))

st.divider()
st.subheader("Recent connector activity")
st.json(store.list_events(limit=30))
