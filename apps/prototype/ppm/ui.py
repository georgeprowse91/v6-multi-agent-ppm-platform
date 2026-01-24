from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import streamlit as st

from .store import Store, Entity
from .security import User, allowed_classifications_for_user, can_access_classification, can_role
from .utils import json_dumps, json_loads


ENTITY_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "intake": {
        "description": "",
        "requester": "",
        "business_unit": "",
        "desired_completion_date": "",
        "size_score": 0.5,
        "complexity_score": 0.5,
        "risk_score": 0.5,
        "attachments": [],
        "tags": [],
    },
    "business_case": {
        "estimated_cost": 250000,
        "annual_benefit": 150000,
        "benefit_years": 3,
        "discount_rate": 0.08,
        "risks": "",
        "assumptions": "",
        "strategic_alignment": 0.6,
        "risk_score": 0.5,
    },
    "portfolio": {"strategy": "", "kpis": {}, "constraints": {"budget_cap": 1000000}},
    "program": {"vision": "", "objectives": [], "kpis": {}},
    "project": {"methodology": "Hybrid", "objectives": [], "scope": "", "assumptions": [], "constraints": [], "stakeholders": []},
    "change_request": {"impact_scope": "Medium", "impact_schedule_days": 10, "impact_cost": 25000, "impact_resources": "Needs review"},
    "release": {"planned_date": "", "readiness": "Not Checked"},
    "knowledge": {"body": "", "tags": []},
    "policy": {"framework": "", "controls": []},
    "resource": {"role": "", "skills": [], "cost_rate": 0, "availability_pct": 100},
}


def entity_picker(store: Store, *, user: User, entity_type: str, label: str) -> Optional[str]:
    entities = [e for e in store.list_entities(type=entity_type, limit=200) if can_access_classification(user.clearance, e.classification)]
    if not entities:
        st.info(f"No {entity_type} records yet.")
        return None
    options = {f"{e.title}  ·  {e.status}  ·  {e.id}": e.id for e in entities}
    chosen = st.selectbox(label, list(options.keys()))
    return options.get(chosen)


def show_entity(store: Store, *, user: User, entity_id: str) -> None:
    ent = store.get_entity(entity_id, include_data=True)
    if not ent:
        st.error("Entity not found.")
        return
    if not can_access_classification(user.clearance, ent.classification):
        st.error("Access denied by classification level.")
        return

    st.markdown(f"### {ent.title}")
    st.caption(f"Type: `{ent.type}` · Status: `{ent.status}` · Classification: `{ent.classification}` · Updated: {ent.updated_at}")

    with st.expander("Data (JSON)", expanded=True):
        st.code(json_dumps(ent.data), language="json")

    # Linked artifacts
    links = store.list_links(ent.id)
    artifact_ids = [l["to_id"] for l in links if l["relation_type"] == "has_artifact" and l["from_id"] == ent.id]
    if artifact_ids:
        st.markdown("#### Artifacts")
        for aid in artifact_ids:
            art = store.get_entity(aid, include_data=True)
            if not art:
                continue
            st.markdown(f"**{art.title}** (`{aid}`)")
            if art.data.get("mime") == "text/markdown":
                st.markdown(art.data.get("content", ""))
            else:
                st.code(json_dumps(art.data), language="json")

    with st.expander("Relations", expanded=False):
        st.json(links)


def entity_create_form(store: Store, *, user: User, entity_type: str, default_title: str = "") -> Optional[str]:
    if not can_role(user.role, "create"):
        st.warning("Your role is not permitted to create records in this prototype.")
        return None

    st.markdown("### Create new")
    title = st.text_input("Title", value=default_title or f"New {entity_type}")
    status = st.text_input("Status", value="Draft")
    allowed_cls = allowed_classifications_for_user(user.clearance)
    classification = st.selectbox("Classification", allowed_cls, index=min(allowed_cls.index("Internal") if "Internal" in allowed_cls else 0, len(allowed_cls)-1))

    template = ENTITY_TEMPLATES.get(entity_type, {})
    data_text = st.text_area("Data JSON", value=json_dumps(template), height=240)

    if st.button("Create", type="primary"):
        try:
            data = json.loads(data_text) if data_text.strip() else {}
        except Exception as e:
            st.error(f"Invalid JSON: {e}")
            return None
        ent = store.create_entity(type=entity_type, title=title, status=status, classification=classification, data=data)
        store.log_event(actor=user.name, event_type="entity_created", entity_id=ent.id, details={"type": entity_type})
        st.success(f"Created {entity_type}: {ent.id}")
        return ent.id
    return None


def entity_edit_form(store: Store, *, user: User, entity_id: str) -> None:
    ent = store.get_entity(entity_id, include_data=True)
    if not ent:
        st.error("Entity not found.")
        return
    if not can_access_classification(user.clearance, ent.classification):
        st.error("Access denied by classification level.")
        return
    if not can_role(user.role, "edit"):
        st.warning("Your role is not permitted to edit records in this prototype.")
        return

    st.markdown("### Edit")
    title = st.text_input("Title", value=ent.title, key=f"edit_title_{entity_id}")
    status = st.text_input("Status", value=ent.status, key=f"edit_status_{entity_id}")
    allowed_cls = allowed_classifications_for_user(user.clearance)
    cls_index = allowed_cls.index(ent.classification) if ent.classification in allowed_cls else 0
    classification = st.selectbox("Classification", allowed_cls, index=cls_index)

    data_text = st.text_area("Data JSON", value=json_dumps(ent.data), height=280)

    cols = st.columns(2)
    with cols[0]:
        if st.button("Save changes", type="primary"):
            try:
                data = json.loads(data_text) if data_text.strip() else {}
            except Exception as e:
                st.error(f"Invalid JSON: {e}")
                return
            store.update_entity(ent.id, title=title, status=status, classification=classification, data=data)
            store.log_event(actor=user.name, event_type="entity_updated", entity_id=ent.id, details={"type": ent.type})
            st.success("Saved.")
    with cols[1]:
        if st.button("Delete", type="secondary"):
            store.delete_entity(ent.id)
            store.log_event(actor=user.name, event_type="entity_deleted", entity_id=ent.id, details={"type": ent.type})
            st.success("Deleted.")
