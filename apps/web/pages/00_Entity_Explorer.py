from __future__ import annotations

import streamlit as st

from ppm.state import get_store
from ppm.session import sidebar_login
from ppm.ui import show_entity

st.set_page_config(page_title="Entity Explorer", layout="wide")

store = get_store()
user = sidebar_login(store)

st.title("Entity Explorer")

st.caption("Browse all records in the prototype store across entity types.")

types = sorted(set(e.type for e in store.list_entities(limit=500)))
chosen_type = st.selectbox("Entity type", types) if types else None
if not chosen_type:
    st.info("No entities yet.")
    st.stop()

entities = store.list_entities(type=chosen_type, limit=200)
labels = [f"{e.title} · {e.status} · {e.id}" for e in entities]
choice = st.selectbox("Select", labels) if labels else None
if not choice:
    st.info("No records of this type.")
    st.stop()

eid = entities[labels.index(choice)].id
show_entity(store, user=user, entity_id=eid)
