from __future__ import annotations

import streamlit as st

from .security import User


def sidebar_login(store) -> User:
    """Render a simple sidebar login and return the active user."""
    st.sidebar.title("Login (prototype)")
    users = store.list_users()
    if not users:
        st.sidebar.warning("No users found in DB.")
        user = User(id="u_guest", name="Guest", email=None, role="Any", clearance="Internal")
        st.session_state["user_id"] = user.id
        st.session_state["user_role"] = user.role
        st.session_state["user_clearance"] = user.clearance
        return user

    # Restore selection if present
    default_idx = 0
    saved_id = st.session_state.get("user_id")
    if saved_id:
        for idx, u in enumerate(users):
            if u.id == saved_id:
                default_idx = idx
                break

    labels = [f"{u.name} · {u.role} · clearance:{u.clearance}" for u in users]
    choice = st.sidebar.selectbox("Select user", labels, index=default_idx)
    user = users[labels.index(choice)]

    st.session_state["user_id"] = user.id
    st.session_state["user_role"] = user.role
    st.session_state["user_clearance"] = user.clearance

    st.sidebar.caption(f"Active: **{user.name}** ({user.role}, clearance={user.clearance})")
    return user
