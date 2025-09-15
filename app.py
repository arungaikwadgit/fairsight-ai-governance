# app.py
import os
import time
import streamlit as st

from config_loader import load_config, get_gates, get_gate_by_id
from auth import ensure_default_users, login, logout
from db import DB
from ui_components import (
    render_topbar, render_footer, render_gate_tabs, render_swimlane_table,
    render_cxo_dashboard, render_add_project_form, render_help_page,
    render_settings_page, render_home_header
)

st.set_page_config(page_title="Fair Sight AI Governance", page_icon="🛡️", layout="wide")

# Load styles
if os.path.exists("styles.css"):
    with open("styles.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

CONFIG = load_config("governance_config.json")
ensure_default_users()

# persistent DB
db = DB()

# ---- Seed default projects if none ----
try:
    if not db.list_projects():
        first_gate = get_gates()[0]["gate_id"] if get_gates() else ""
        demo_now = time.time()
        for name in ["AI Risk Scoring Pilot", "Customer Chatbot Revamp", "Forecast Model V2"]:
            db.create_project({
                "name": name,
                "description": "Demo project seeded on first run",
                "owner": "demo_owner",
                "type": "Prototype",
                "start_date": "",
                "status": "ONGOING",
                "current_gate_id": first_gate,
                "created_at": demo_now,
                "updated_at": demo_now
            })
except Exception as _e:
    pass

def set_page(page):
    st.session_state["page"] = page

if "page" not in st.session_state:
    st.session_state["page"] = "Login"

# Top Bar & Menu
render_topbar()

with st.sidebar:
    st.markdown("### Menu")
    if "auth_user" not in st.session_state:
        if st.button("Login", use_container_width=True):
            set_page("Login")
    else:
        if st.button("Home", use_container_width=True):
            set_page("Home")
        if st.button("CXO Dashboard", use_container_width=True):
            set_page("CXO Dashboard")
        if st.button("Add Project", use_container_width=True):
            set_page("Add Project")
        if st.session_state.get("role","") == "ChiefAIOfficer":
            if st.button("Settings", use_container_width=True):
                set_page("Settings")
        if st.button("Help", use_container_width=True):
            set_page("Help")
        st.divider()
        st.caption(f"Signed in as **{st.session_state.get('auth_user')}** ({st.session_state.get('role')})")
        if st.button("Sign out", use_container_width=True):
            logout()
            set_page("Login")
            st.rerun()

# ------------- Pages -------------

def page_login():
    st.header("Sign in")
    col1, col2 = st.columns([3,2])
    with col1:
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", type="primary")  # Enter triggers submit
        if submitted:
            if login(username, password):
                st.success("Signed in.")
                set_page("Home")
                st.rerun()
            else:
                st.error("Invalid username or password.")
    with col2:
        st.image("assets/logo.png", caption="Fair Sight AI Governance", use_column_width=True)

def page_home():
    render_home_header(db)
    gates = get_gates()
    if not gates:
        st.error("No gates found. Please ensure governance_config.json is present and has a 'gates' array.")
        return
    active_tab, gate_ids = render_gate_tabs(gates, db)
    gate = get_gate_by_id(active_tab, gates)
    if not gate:
        st.info("No gate selected.")
        return
    render_swimlane_table(db, gate, CONFIG)

def page_cxo_dashboard():
    render_cxo_dashboard(db)

def page_add_project():
    render_add_project_form(db)

def page_settings():
    if st.session_state.get("role","") != "ChiefAIOfficer":
        st.error("Settings are restricted to the Chief AI Officer.")
        return
    render_settings_page(db)

def page_help():
    render_help_page(CONFIG)

# ---------- Router ----------

if st.session_state["page"] == "Login" and "auth_user" in st.session_state:
    set_page("Home")

page = st.session_state["page"]
if page == "Login":
    page_login()
elif page == "Home":
    if "auth_user" not in st.session_state:
        page_login()
    else:
        page_home()
elif page == "CXO Dashboard":
    page_cxo_dashboard() if "auth_user" in st.session_state else page_login()
elif page == "Add Project":
    page_add_project() if "auth_user" in st.session_state else page_login()
elif page == "Settings":
    page_settings() if "auth_user" in st.session_state else page_login()
elif page == "Help":
    page_help()
else:
    st.write("Page not found.")

render_footer()
