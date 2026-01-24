from __future__ import annotations

import streamlit as st

from .bootstrap import bootstrap
from .store import Store


@st.cache_resource
def get_store() -> Store:
    return bootstrap()
