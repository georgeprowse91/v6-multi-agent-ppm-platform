from __future__ import annotations

import streamlit as st

from ppm.state import get_store
from ppm.session import sidebar_login
from ppm.requirements import load_requirements

st.set_page_config(page_title="Requirements", layout="wide")

store = get_store()
user = sidebar_login(store)

st.title("Requirements")
payload = load_requirements()

st.caption(f"Loaded from: `{payload.get('source','requirements.json')}`")

tabs = st.tabs(["Functional domains", "Non-functional requirements"])

with tabs[0]:
    domains = payload.get("functional_domains", [])
    for d in domains:
        title = d.get("title")
        reqs = d.get("requirements", [])
        with st.expander(title, expanded=False):
            for i, r in enumerate(reqs, start=1):
                st.markdown(f"**{i}.** {r}")

with tabs[1]:
    nfr = payload.get("non_functional_requirements", [])
    for i, r in enumerate(nfr, start=1):
        st.markdown(f"**{i}.** {r}")
