from __future__ import annotations

import streamlit as st

from ppm.state import get_store
from ppm.session import sidebar_login
from ppm.docs import list_docx, extract_docx_text, search_docx

st.set_page_config(page_title="Docs & Specs Viewer", layout="wide")

store = get_store()
user = sidebar_login(store)

st.title("Docs & Specs Viewer")

st.markdown(
    """This page lets you browse the repository’s DOCX specifications directly in the prototype.

It extracts text using `python-docx` and is meant for quick review/search (not pixel-perfect rendering)."""
)

q = st.text_input("Search query (substring match)", value="")
if q.strip():
    st.subheader("Search results")
    res = search_docx(q.strip(), max_results=30)
    if not res:
        st.info("No matches.")
    else:
        for r in res:
            st.markdown(f"- **{r['title']}** ({r['group']}) — `{r['path']}`")

st.divider()
st.subheader("Browse documents")

docs = list_docx()
if not docs:
    st.warning("No DOCX files found under repo `docs/`, `specs/`, or `integrations/`.")
else:
    labels = [f"[{d.group}] {d.title}" for d in docs]
    choice = st.selectbox("Select a document", labels)
    d = docs[labels.index(choice)]

    st.caption(d.path)
    text = extract_docx_text(d.path, max_paragraphs=2000)
    st.text_area("Extracted text", value=text, height=520)
