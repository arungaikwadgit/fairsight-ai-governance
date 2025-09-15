# auth.py
import streamlit as st
import hashlib

USERS = {
    "caios": {"password_hash": "", "role": "ChiefAIOfficer"},
    "governance1": {"password_hash": "", "role": "GovernanceReviewer"},
}

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def ensure_default_users():
    if "user_passwords" not in st.session_state:
        USERS["caios"]["password_hash"] = _hash("admin123")
        USERS["governance1"]["password_hash"] = _hash("review123")
        st.session_state["user_passwords"] = USERS

def login(username: str, password: str) -> bool:
    users = st.session_state.get("user_passwords", {})
    u = users.get(username)
    if not u:
        return False
    ok = u["password_hash"] == _hash(password)
    if ok:
        st.session_state["auth_user"] = username
        st.session_state["role"] = u["role"]
    return ok

def logout():
    for k in ["auth_user","role"]:
        if k in st.session_state:
            del st.session_state[k]

def get_current_user_role(username: str) -> str:
    users = st.session_state.get("user_passwords", {})
    return users.get(username, {}).get("role", "Viewer")
