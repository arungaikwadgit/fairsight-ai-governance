# ui_components.py
import streamlit as st
import time
from typing import List, Dict, Any
from rbac import is_caio, is_reviewer_for
from workflow import DECISIONS, compute_gate_status
from config_loader import get_gates

def render_topbar():
    from pathlib import Path
    cols = st.columns([1,6,2])
    with cols[0]:
        if st.session_state.get("page") != "Login":
            logo_path = Path(__file__).parent / "assets" / "logo.png"
            if logo_path.exists():
                st.image(str(logo_path), use_column_width=True)
            else:
                st.markdown("<div style='width:48px;height:48px;border-radius:12px;background:linear-gradient(45deg,#0b5ed7,#dc3545)'></div>", unsafe_allow_html=True)
    with cols[1]:
        st.markdown('<div class="app-title">Fair Sight AI Governance</div>', unsafe_allow_html=True)
    with cols[2]:
        if "auth_user" in st.session_state:
            st.caption(f"Signed in as **{st.session_state.get('auth_user')}** ({st.session_state.get('role')})")

def render_footer():
    st.markdown(
        "<div class='app-footer'>© Arun Gaikwad, Software Engg Manager</div>",
        unsafe_allow_html=True,
    )

def render_home_header(db):
    st.subheader("Home — Swimlane")
    projects = db.list_projects()
    if not projects:
        st.info("No projects yet. Use 'Add Project' to create one.")
        return
    options = {f"{p['name']} ({p['status']})": p["id"] for p in projects}
    choice = st.selectbox("Project", options.keys(), key="home_project_sel")
    st.session_state["open_project"] = options[choice]

def render_gate_tabs(gates: List[Dict[str,Any]], db):
    labels = [g["gate_name"] for g in gates]
    if "active_gate" not in st.session_state:
        st.session_state["active_gate"] = labels[0] if labels else ""
    chosen = st.radio("Gates", labels, horizontal=True, label_visibility="collapsed",
                      index=labels.index(st.session_state["active_gate"]) if st.session_state["active_gate"] in labels else 0)
    st.session_state["active_gate"] = chosen
    return chosen, labels

def _artifact_modal_key(gate_id, artifact_key):
    return f"artifact_modal_{gate_id}_{artifact_key}"

def _ai_modal_key(gate_id, artifact_key):
    return f"ai_modal_{gate_id}_{artifact_key}"

def render_swimlane_table(db, gate_obj: Dict[str,Any], CONFIG: Dict[str,Any]):
    # ---- Setup & context ----
    pid = st.session_state.get("open_project")
    if not pid:
        st.info("Select a project above.")
        return

    proj = db.get_project(pid)
    role = st.session_state.get("role", "")

    # Current gate state from inline DB
    gate_state = proj.get("gates", {}).get(gate_obj["gate_id"], {})
    cp_map = gate_state.get("checkpoints", {})

    decisions = [
        cp_map.get(cp["artifact_key"], {}).get("decision", "Pending")
        for cp in gate_obj["checkpoints"]
    ]

    # If CAIO overrode the gate, show the override as the overall status.
    # If CAIO overrode the gate, show the override as the overall status.
    if gate_state.get("overridden"):
        overall = gate_state.get("gate_status", "Pending")
        st.markdown(f"**Overall Gate Status (CAIO Override):** :blue[{overall}]")
        st.caption(
            f"Overridden by {gate_state.get('override_by','CAIO')}: "
            f"{gate_state.get('override_reason','')}"
        )
    else:
        overall = compute_gate_status(decisions)
        st.markdown(f"**Overall Gate Status:** :blue[{overall}]")


    # ---- Table header ----
    cols = st.columns([3, 3, 2, 2, 3])
    cols[0].markdown("**Checkpoint**")
    cols[1].markdown("**Artifact**")
    cols[2].markdown("**Submitted By**")
    cols[3].markdown("**Reviewed By**")
    cols[4].markdown("**Decision / AI**")

    # ---- Rows ----
    for cp in gate_obj["checkpoints"]:
        row = st.columns([3, 3, 2, 2, 3])

        # Left cell: clickable checkpoint name opens the artifact editor
        if row[0].button(cp["artifact"], key=f"cp_{gate_obj['gate_id']}_{cp['artifact_key']}_name"):
            st.session_state[_artifact_modal_key(gate_obj["gate_id"], cp["artifact_key"])] = True

        row[1].write(cp["artifact"])
        row[2].write(cp.get("submitted_by_role", ""))
        row[3].write(cp.get("reviewed_by_role", ""))

        # Decision + AI Suggestion
        dcol1, dcol2 = row[4].columns([1, 1])
        cur_decision = cp_map.get(cp["artifact_key"], {}).get("decision", "Pending")
        reviewer_only = is_reviewer_for(cp, role)

        # If the gate is overridden, force the dropdown to the override value and lock it
        override_active = gate_state.get("overridden", False)
        override_value  = gate_state.get("gate_status", "Pending") if override_active else None
        effective_decision = override_value if override_active else cur_decision

        with dcol1:
            new_decision = st.selectbox(
                "Decision",                              # non-empty label for accessibility
                DECISIONS,
                index=DECISIONS.index(effective_decision) if effective_decision in DECISIONS else DECISIONS.index("Pending"),
                key=f"dec_{gate_obj['gate_id']}_{cp['artifact_key']}",
                disabled=True if override_active else not reviewer_only,   # lock if overridden
                label_visibility="collapsed",
            )

        if reviewer_only and not override_active and new_decision != cur_decision:
            db.save_checkpoint_decision(
                pid,
                gate_obj["gate_id"],
                cp["artifact_key"],
                new_decision,
                st.session_state.get("auth_user", "unknown"),
            )
            st.rerun()


        with dcol2:
            ai_click = st.button(
                "Get AI Suggestion",
                key=f"ai_{gate_obj['gate_id']}_{cp['artifact_key']}",
                disabled=not reviewer_only,
            )
            if ai_click:
                st.session_state[_ai_modal_key(gate_obj["gate_id"], cp["artifact_key"])] = True

        # Persist decision (only reviewer/CAIO)
        if reviewer_only and new_decision != cur_decision:
            db.save_checkpoint_decision(
                pid,
                gate_obj["gate_id"],
                cp["artifact_key"],
                new_decision,
                st.session_state.get("auth_user", "unknown"),
            )
            st.rerun()

        # ----- Artifact "modal" (container) -----
        if st.session_state.get(_artifact_modal_key(gate_obj["gate_id"], cp["artifact_key"])):
            st.markdown("---")
            st.markdown(f"### Artifact — {cp['artifact']}")
            payload = cp_map.get(cp["artifact_key"], {}).get("payload", {})
            with st.form(f"artifact_form_{gate_obj['gate_id']}_{cp['artifact_key']}", clear_on_submit=False):
                desc = st.text_area("Description / Evidence", value=payload.get("desc", ""))
                link = st.text_input("Link to evidence (optional)", value=payload.get("link", ""))
                notes = st.text_area("Notes", value=payload.get("notes", ""))

                c1, c2 = st.columns(2)
                save = c1.form_submit_button("Save", type="primary")
                close = c2.form_submit_button("Close")

            if save:
                db.save_checkpoint_payload(
                    pid,
                    gate_obj["gate_id"],
                    cp["artifact_key"],
                    {"desc": desc, "link": link, "notes": notes},
                    st.session_state.get("auth_user", "unknown"),
                )
                st.session_state[_artifact_modal_key(gate_obj["gate_id"], cp["artifact_key"])] = False
                st.rerun()

            if close:
                st.session_state[_artifact_modal_key(gate_obj["gate_id"], cp["artifact_key"])] = False
                st.rerun()

        # ----- AI Suggestion "modal" (container) -----
        if st.session_state.get(_ai_modal_key(gate_obj["gate_id"], cp["artifact_key"])):
            st.markdown("---")
            st.markdown("### AI Suggestion")
            from ai import recommend_for_checkpoint
            suggestion = recommend_for_checkpoint(proj, gate_obj, cp)
            st.code(suggestion, language="markdown")

            c1, c2 = st.columns(2)
            apply_click = c1.button(
                "Apply Suggestion",
                key=f"apply_{gate_obj['gate_id']}_{cp['artifact_key']}",
            )
            dismiss_click = c2.button(
                "Dismiss",
                key=f"dismiss_{gate_obj['gate_id']}_{cp['artifact_key']}",
            )

            if apply_click:
                decision = (
                    "Approve" if "Suggested decision:** Approve" in suggestion
                    else "Reject" if "Suggested decision:** Reject" in suggestion
                    else "ReScope" if "Suggested decision:** ReScope" in suggestion
                    else "Pending"
                )
                db.save_checkpoint_decision(
                    pid,
                    gate_obj["gate_id"],
                    cp["artifact_key"],
                    decision,
                    st.session_state.get("auth_user", "unknown"),
                )
                st.session_state[_ai_modal_key(gate_obj["gate_id"], cp["artifact_key"])] = False
                st.rerun()

            if dismiss_click:
                st.session_state[_ai_modal_key(gate_obj["gate_id"], cp["artifact_key"])] = False
                st.rerun()

    # ----- CAIO override for gate status -----
    if st.session_state.get("role", "") == "ChiefAIOfficer":
        with st.expander("CAIO Override Gate Status"):
            choice = st.selectbox(
                "Set gate status",
                DECISIONS,
                index=DECISIONS.index(overall) if overall in DECISIONS else DECISIONS.index("Pending"),
            )
            reason = st.text_input("Reason")
            if st.button("Apply Override"):
                user = st.session_state.get("auth_user", "unknown")
                # 1) Save gate override
                db.save_gate_status(pid, gate_obj["gate_id"], choice, user, reason)
                # 2) Apply the same decision to ALL checkpoints in this gate
                for cp in gate_obj["checkpoints"]:
                    db.save_checkpoint_decision(pid, gate_obj["gate_id"], cp["artifact_key"], choice, user)
                st.success("Gate status overridden and checkpoint decisions updated.")
                st.rerun()


def render_cxo_dashboard(db):
    import pandas as pd
    st.subheader("CXO Dashboard")

    projects = db.list_projects()
    if not projects:
        st.info("No projects yet. Add a project to see the dashboard.")
        return

    # ---- Aggregate per-gate status across all projects ----
    total = len(projects)
    gate_status_counts = {"Approve": 0, "Reject": 0, "Pending": 0, "ReScope": 0}
    proj_status_counts = {"ONGOING": 0, "COMPLETED": 0, "PENDING": 0}

    latest_rows = []
    for p in projects:
        proj_status_counts[p.get("status", "ONGOING").upper()] = proj_status_counts.get(p.get("status","ONGOING").upper(), 0) + 1
        gates = p.get("gates", {})
        # find latest updated gate if any
        latest_gid = None
        latest_ts = -1
        latest_status = "Pending"
        for gid, gs in gates.items():
            ts = 0
            # try to infer latest timestamp from audit trail
            for ev in gs.get("audit", []):
                ts = max(ts, ev.get("ts", 0))
            if ts > latest_ts:
                latest_ts = ts
                latest_gid = gid
                latest_status = gs.get("gate_status", "Pending")
            # aggregate counts
            gate_status_counts[gs.get("gate_status", "Pending")] = gate_status_counts.get(gs.get("gate_status","Pending"), 0) + 1

        latest_rows.append({
            "Project": p.get("name",""),
            "Current Gate": p.get("current_gate_id",""),
            "Latest Gate Touched": latest_gid or p.get("current_gate_id",""),
            "Latest Gate Status": latest_status,
            "Owner": p.get("owner","")
        })

    # ---- KPI tiles ----
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Projects", total)
    c2.metric("Gates Approved", gate_status_counts.get("Approve", 0))
    c3.metric("Gates Pending", gate_status_counts.get("Pending", 0))
    c4.metric("Gates Rejected", gate_status_counts.get("Reject", 0))

    st.divider()

    # ---- Visualization: bar chart of gate status distribution ----
    status_df = pd.DataFrame.from_dict(gate_status_counts, orient="index", columns=["count"]).sort_index()
    st.caption("Gate status distribution")
    st.bar_chart(status_df)

    st.divider()

    # ---- Recent / latest activity table ----
    st.caption("Latest project activity")
    latest_df = pd.DataFrame(latest_rows)
    st.dataframe(latest_df, use_container_width=True, hide_index=True)

    # ---- Project status counts (optional small chart) ----
    proj_df = pd.DataFrame.from_dict(proj_status_counts, orient="index", columns=["count"]).sort_index()
    st.caption("Project status overview")
    st.bar_chart(proj_df)

def render_add_project_form(db):
    import time as _t
    from config_loader import get_gates
    st.subheader("Add Project")
    with st.form("add_project_form", clear_on_submit=False):
        name = st.text_input("Project name")
        desc = st.text_area("Description")
        owner = st.text_input("Owner")
        submitted = st.form_submit_button("Create", type="primary")
    if submitted:
        if not name.strip():
            st.warning("Project name is required.")
            return
        gates = get_gates()
        first_gate = gates[0]["gate_id"] if gates else ""
        pid = db.create_project({
            "name": name.strip(),
            "description": desc.strip(),
            "owner": owner.strip(),
            "status": "ONGOING",
            "current_gate_id": first_gate,
            "created_at": _t.time(),
            "updated_at": _t.time()
        })
        st.success(f"Created project: {name}")
        st.session_state["open_project"] = pid
        st.rerun()

def render_help_page(CONFIG):
    st.subheader("Help")
    st.markdown("#### Roles and Responsibilities")
    roles = CONFIG.get("roles", [])
    if roles:
        for r in roles:
            st.markdown(f"- **{r.get('role','')}** — {r.get('permissions','')}")
    else:
        st.info("No roles found in configuration.")
    st.divider()
    st.markdown("#### How to Use the Application")
    st.markdown("""
1. **Login** with your username/password. Your role controls access.
2. Go to **Home** to view the swimlane. Choose a project from the dropdown.
3. Click a checkpoint name to open its **Artifact** editor. Add evidence/notes and save.
4. As a **Reviewer/CAIO**, use the **Decision** dropdown or click **Get AI Suggestion** to get a recommendation.
5. The **Overall Gate Status** updates automatically from checkpoint decisions.
6. Only when a gate is **Approved** can the next gate proceed.
7. **CXO Dashboard** shows status KPIs and charts.
8. **Add Project** creates a new project.
9. **Settings (CAIO)** lets the Chief AI Officer set the OpenAPI key and model for AI suggestions.
    """)

def render_settings_page(db):
    from rbac import is_caio
    st.subheader("Settings")
    role = st.session_state.get("role","")
    if not is_caio(role):
        st.error("Settings are restricted to the Chief AI Officer.")
        return
    st.markdown("Manage OpenAPI credentials used for AI recommendations.")
    current = db.get_settings()
    with st.form("settings_form", clear_on_submit=False):
        api_key = st.text_input("OpenAPI Key", type="password", value="", help="Key is stored obfuscated locally.")
        model = st.text_input("Model (e.g., gpt-4o-mini)", value=current.get("openapi_model","gpt-4o-mini"))
        c1, c2 = st.columns(2)
        save = c1.form_submit_button("Save", type="primary")
        clear = c2.form_submit_button("Clear Key")
    if save:
        db.save_openapi_key(api_key.strip(), model.strip() if model.strip() else None)
        st.success("Settings saved.")
        st.rerun()
    if clear:
        db.clear_openapi_key()
        st.success("API key cleared.")
        st.rerun()
