# app.py
import os
import json
import time
import streamlit as st
from pathlib import Path
from typing import Dict, Any, List

from auth import login, get_current_user_role, ensure_default_users
from firestore_db import DB
from workflow import WORKFLOW_GATES, can_advance_gate, gate_requirements_text
from ai import recommend_next_steps, train_policy_notes

st.set_page_config(page_title="Fair Sight AI Governance", page_icon="assets/logo.png", layout="wide")

# Inject Tailwind-like utility styles (subset) for Streamlit via CSS
with open("styles.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Header
logo_col, title_col = st.columns([1,6])
with logo_col:
    st.image("assets/logo.png", use_column_width=True)
with title_col:
    st.markdown('<div class="app-title">Fair Sight AI Governance</div>', unsafe_allow_html=True)
    st.caption("Track AI projects, enforce ethical gates, and use AI to recommend next steps.")

# Auth
ensure_default_users()
st.divider()
st.subheader("Sign in")
username = st.text_input("Username", key="user")
password = st.text_input("Password", type="password", key="pwd")
if st.button("Sign in", type="primary"):
    if login(username, password):
        st.session_state["auth_user"] = username
        st.session_state["role"] = get_current_user_role(username)
        st.success(f"Welcome, {username}! Role: {st.session_state['role']}")
    else:
        st.error("Invalid username or password.")

if "auth_user" not in st.session_state:
    st.stop()

role = st.session_state["role"]
db = DB()

st.divider()
st.subheader("Project Dashboard")

# Create new project (project owner or CAIO)
with st.expander("➕ Create New Project"):
    pname = st.text_input("Project Name")
    pdesc = st.text_area("Brief Description")
    if st.button("Create Project"):
        if pname.strip():
            pid = db.create_project({
                "name": pname.strip(),
                "description": pdesc.strip(),
                "owner": st.session_state["auth_user"],
                "status": "ONGOING",
                "current_gate_index": 0,
                "artifacts": {},  # gate_index -> list of {name, path/url}
                "ethics_checks": {},
                "created_at": time.time(),
                "updated_at": time.time(),
            })
            st.success(f"Created project: {pname} (ID: {pid})")
        else:
            st.warning("Project name required.")

# Project list
projects = db.list_projects()
if not projects:
    st.info("No projects yet. Create one above.")
else:
    for p in projects:
        with st.container(border=True):
            left, mid, right = st.columns([3,3,2])
            with left:
                st.markdown(f"**{p['name']}**")
                st.caption(p.get("description",""))
                st.text(f"Owner: {p.get('owner','')}")
            with mid:
                gate_idx = p.get("current_gate_index", 0)
                st.text(f"Stage: {gate_idx+1}/{len(WORKFLOW_GATES)} — {WORKFLOW_GATES[gate_idx]['name']}")
                st.progress(int((gate_idx+1)/len(WORKFLOW_GATES)*100))
            with right:
                st.text(f"Status: {p.get('status','')}")
                if st.button("Open", key=f"open_{p['id']}"):
                    st.session_state["open_project"] = p["id"]

# Detail view
if "open_project" in st.session_state:
    pid = st.session_state["open_project"]
    proj = db.get_project(pid)
    if not proj:
        st.error("Project not found.")
    else:
        st.header(f"Project: {proj['name']}")
        st.caption(proj.get("description",""))
        gate_idx = proj.get("current_gate_index", 0)
        current_gate = WORKFLOW_GATES[gate_idx]

        # Artifacts for current gate
        st.subheader(f"Current Gate: {current_gate['name']}")
        st.markdown(gate_requirements_text(current_gate))

        with st.expander("Upload artifacts for this gate"):
            uploaded = st.file_uploader("Upload files", accept_multiple_files=True)
            if uploaded:
                saved_paths = []
                for uf in uploaded:
                    # Save locally (demo); in Firebase variation we'd push to Storage
                    save_dir = Path("uploads") / pid / f"gate_{gate_idx}"
                    save_dir.mkdir(parents=True, exist_ok=True)
                    path = save_dir / uf.name
                    with open(path, "wb") as f:
                        f.write(uf.getbuffer())
                    saved_paths.append(str(path))
                db.add_artifacts(pid, gate_idx, saved_paths)
                st.success(f"Uploaded {len(saved_paths)} artifact(s).")

        st.divider()
        # AI Recommendation panel
        st.subheader("AI Recommendation Model")
        st.caption("Get next-step guidance based on project details, artifacts, and ethical criteria.")
        if st.button("Generate Recommendations"):
            with st.spinner("Consulting AI..."):
                recs = recommend_next_steps(proj, db.get_project_artifacts(pid, gate_idx))
            st.success("Recommendations ready.")
            st.code(recs, language="markdown")

        if role == "ChiefAIOfficer":
            st.markdown("**Admin: Policy Training Notes**")
            new_notes = st.text_area("Add/Update policy notes (feeds the AI prompt)")
            if st.button("Save Policy Notes"):
                train_policy_notes(new_notes)
                st.success("Policy notes saved. Future recommendations will consider these.")

        st.divider()
        # Advancement controls
        st.subheader("Gate Review")
        approve = st.checkbox("Approve this gate (meets ethical criteria).")
        if st.button("Advance to Next Gate"):
            if can_advance_gate(proj, db, approve):
                db.advance_gate(pid)
                st.success("Advanced to the next gate.")
                st.experimental_rerun()
            else:
                st.error("Cannot advance: missing artifacts or approval.")

        st.divider()
        if st.button("Mark Project Complete"):
            db.update_project(pid, {"status": "COMPLETED"})
            st.success("Project marked completed.")
            st.experimental_rerun()
