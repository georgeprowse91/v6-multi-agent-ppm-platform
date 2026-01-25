from __future__ import annotations

import json

import streamlit as st
from ppm.session import sidebar_login
from ppm.state import get_store
from ppm.utils import json_dumps
from ppm.workflows.engine import advance_workflow, start_workflow

st.set_page_config(page_title="Workflows", layout="wide")

store = get_store()
user = sidebar_login(store)

st.title("Workflow & Process Engine (Prototype)")

defs = store.list_workflow_defs()
if not defs:
    st.warning("No workflow definitions found. Check `apps/web/data/workflows/*.json`.")
else:
    with st.expander("Workflow definitions", expanded=False):
        for d in defs:
            st.markdown(f"### {d['name']}  ")
            st.caption(
                f"id={d['id']} · version={d['version']} · entity_type={d['entity_type']} · active={bool(d['active'])}"
            )
            st.code(json_dumps(d.get("def", {})), language="json")

st.divider()
st.subheader("Start workflow instance")

wf_opts = {f"{d['name']} ({d['id']})": d["id"] for d in defs if d.get("active") == 1}
chosen = st.selectbox("Workflow", list(wf_opts.keys())) if wf_opts else None
entity_id = st.text_input("Entity id")
if st.button("Start", type="primary"):
    try:
        iid = start_workflow(store, def_id=wf_opts[chosen], entity_id=entity_id.strip(), actor=user.name)  # type: ignore
        st.success(f"Started workflow instance: {iid}")
    except Exception as e:
        st.error(str(e))

st.divider()
st.subheader("Active instances")

instances = store.list_workflow_instances(limit=100)
if not instances:
    st.info("No workflow instances yet.")
else:
    for inst in instances:
        with st.expander(
            f"{inst['id']} · {inst['status']} · entity={inst['entity_id']} · step={inst.get('current_step_id')}",
            expanded=False,
        ):
            wf = store.get_workflow_def(inst["def_id"])
            wf_def = (wf or {}).get("def", {})
            st.caption(f"Workflow: {(wf or {}).get('name')} ({inst['def_id']})")
            st.json(inst.get("context", {}))

            current_step_id = inst.get("current_step_id")
            if current_step_id:
                # Find step details
                step = None
                for s in wf_def.get("steps", []):
                    if s.get("id") == current_step_id:
                        step = s
                        break
                if step:
                    st.markdown(f"**Current step:** {step.get('name')} (`{current_step_id}`)")
                    st.code(json_dumps(step), language="json")

                    inputs_text = st.text_area(
                        "Agent inputs (JSON)", value="{}", height=90, key=f"inputs_{inst['id']}"
                    )
                    approve = None
                    if step.get("gate"):
                        approve = st.radio(
                            "Approval decision",
                            options=["(not set)", "Approve", "Reject"],
                            horizontal=True,
                            key=f"approve_{inst['id']}",
                        )
                    if st.button("Advance", key=f"advance_{inst['id']}", type="primary"):
                        try:
                            inp = json.loads(inputs_text) if inputs_text.strip() else {}
                            decision = None
                            if approve == "Approve":
                                decision = True
                            elif approve == "Reject":
                                decision = False
                            out = advance_workflow(
                                store,
                                instance_id=inst["id"],
                                actor=user.name,
                                approve=decision,
                                agent_inputs=inp,
                            )
                            st.success("Advanced.")
                            st.json(out)
                        except Exception as e:
                            st.error(str(e))
