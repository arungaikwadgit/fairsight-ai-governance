# auth.py
import streamlit as st
import hashlib

# Simple in-memory user store with hashed passwords (demo-friendly).
# For production, use Firestore users collection or an IdP.
DEFAULT_USERS = {
    "caios": {"password_hash": "", "role": "ChiefAIOfficer"},
    "governance1": {"password_hash": "", "role": "GovernanceReviewer"},
}

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def ensure_default_users():
    # Set default demo passwords if not already set in session_state
    # You can change these via environment variables for quick tests
    if "user_passwords" not in st.session_state:
        caios_pw = _hash("admin123")
        gov_pw = _hash("review123")
        DEFAULT_USERS["caios"]["password_hash"] = caios_pw
        DEFAULT_USERS["governance1"]["password_hash"] = gov_pw
        st.session_state["user_passwords"] = DEFAULT_USERS

def login(username: str, password: str) -> bool:
    users = st.session_state.get("user_passwords", {})
    u = users.get(username)
    if not u:
        return False
    return u["password_hash"] == _hash(password)

def get_current_user_role(username: str) -> str:
    users = st.session_state.get("user_passwords", {})
    return users.get(username, {}).get("role", "Viewer")
