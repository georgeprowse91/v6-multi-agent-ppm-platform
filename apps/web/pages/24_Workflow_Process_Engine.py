from __future__ import annotations

import json
import streamlit as st

from ppm.state import get_store
from ppm.session import sidebar_login
from ppm.agents.registry import run_agent
from ppm.utils import json_dumps, json_dumps_compact

st.set_page_config(page_title="Workflow & Process Engine", layout="wide")

store = get_store()
user = sidebar_login(store)

st.title("Workflow & Process Engine")

st.markdown(
    """This page focuses on **workflow definitions** (templates) and configuration.

For **running** workflows (instances, gate decisions, step execution), use the **Workflows** page."""
)

st.divider()
st.subheader("Current workflow templates")

defs = store.list_workflow_defs()
if not defs:
    st.warning("No workflow definitions found. Ensure `apps/web/data/workflows/*.json` exists.")
else:
    for d in defs:
        with st.expander(f"{d['name']} · id={d['id']} · active={bool(d['active'])}", expanded=False):
            st.caption(f"entity_type={d['entity_type']} · version={d['version']}")
            active = st.checkbox("Active", value=bool(d["active"]), key=f"active_{d['id']}")
            if st.button("Save active flag", key=f"save_active_{d['id']}"):
                # Keep same JSON def; toggle active
                store.upsert_workflow_def(
                    wf_id=d["id"],
                    name=d["name"],
                    version=d["version"],
                    entity_type=d["entity_type"],
                    json_def=json_dumps_compact(d.get("def", {})),
                    active=active,
                )
                store.log_event(actor=user.name, event_type="workflow_def_updated", entity_id=None, details={"wf_id": d["id"], "active": active})
                st.success("Updated.")

            st.code(json_dumps(d.get("def", {})), language="json")

st.divider()
st.subheader("Add / update a workflow template (JSON)")

wf_json_text = st.text_area(
    "Workflow JSON",
    height=260,
    value=json_dumps(
        {
            "id": "wf_example",
            "name": "Example Workflow",
            "version": "1.0",
            "entity_type": "project",
            "steps": [
                {"id": "step1", "name": "Example step", "agent_id": 9, "next": ["end"]},
                {"id": "end", "name": "End", "terminal": True},
            ],
        }
    ),
)
if st.button("Upsert workflow template", type="primary"):
    try:
        wf = json.loads(wf_json_text) if wf_json_text.strip() else {}
        store.upsert_workflow_def(
            wf_id=wf["id"],
            name=wf.get("name", wf["id"]),
            version=wf.get("version", "1.0"),
            entity_type=wf.get("entity_type", "unknown"),
            json_def=json_dumps_compact(wf),
            active=True,
        )
        store.log_event(actor=user.name, event_type="workflow_def_upserted", entity_id=None, details={"wf_id": wf["id"]})
        st.success("Workflow template saved.")
    except Exception as e:
        st.error(str(e))

st.divider()
st.subheader("Inspect via Agent 24 (stub)")

if st.button("Run Agent 24", type="secondary"):
    out = run_agent(store, agent_id=24, actor=user.name, entity_id=None, inputs={})
    st.json(out)
