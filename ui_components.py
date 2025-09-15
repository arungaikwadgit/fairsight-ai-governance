# ui_components.py
from typing import List, Dict, Any, Optional
import time
import streamlit as st

from rbac import is_caio, is_reviewer_for
from workflow import DECISIONS, compute_gate_status
from config_loader import get_gates

# ---------- Top / Footer ----------

def render_topbar():
    from pathlib import Path
    cols = st.columns([1, 6, 2])
    with cols[0]:
        if st.session_state.get("page") != "Login":
            logo_path = Path(__file__).parent / "assets" / "logo.png"
            if logo_path.exists():
                st.image(str(logo_path), use_column_width=True)
            else:
                # Fallback if logo missing
                st.markdown(
                    "<div style='width:48px;height:48px;border-radius:12px;"
                    "background:linear-gradient(45deg,#0b5ed7,#dc3545)'></div>",
                    unsafe_allow_html=True,
                )
    with cols[1]:
        st.markdown('<div class="app-title">Fair Sight AI Governance</div>', unsafe_allow_html=True)
    with cols[2]:
        if "auth_user" in st.session_state:
            st.caption(f"Signed in as **{st.session_state.get('auth_user')}** ({st.session_state.get('role')})")

def render_footer():
    # Styled via .app-footer in styles.css (blue background, white text)
    st.markdown("<div class='app-footer'>© Arun Gaikwad, Software Engg Manager</div>", unsafe_allow_html=True)

# ---------- Home Header / Gate Tabs ----------

def render_home_header(db):
    st.subheader("Home — Swimlane")
    projects = db.list_projects()
    if not projects:
        st.info("No projects yet. Use 'Add Project' to create one.")
        return
    options = {f"{p['name']} ({p['status']})": p["id"] for p in projects}
    choice = st.selectbox("Select Project", options.keys(), key="home_project_sel")
    st.session_state["open_project"] = options[choice]

def render_gate_tabs(gates: List[Dict[str, Any]], db):
    # Show tabs as "G#-<GateName>" while keeping internal gate_id
    label_map = {f"{g['gate_id']}-{g['gate_name']}": g["gate_id"] for g in gates}
    labels = list(label_map.keys())

    if "active_gate" not in st.session_state and labels:
        st.session_state["active_gate"] = label_map[labels[0]]

    try:
        default_idx = labels.index(next(lbl for lbl, gid in label_map.items() if gid == st.session_state.get("active_gate")))
    except StopIteration:
        default_idx = 0

    chosen_label = st.radio(
        "Gates",
        labels,
        horizontal=True,
        label_visibility="collapsed",
        index=default_idx if labels else 0,
    )
    chosen_gate_id = label_map[chosen_label]
    st.session_state["active_gate"] = chosen_gate_id
    return chosen_gate_id, [g["gate_id"] for g in gates]

# ---------- Keys for session "modals" ----------

def _artifact_modal_key(gate_id: str, artifact_key: str) -> str:
    return f"artifact_modal_{gate_id}_{artifact_key}"

def _ai_modal_key(gate_id: str, artifact_key: str) -> str:
    return f"ai_modal_{gate_id}_{artifact_key}"

# ---------- Swimlane Table (main home UI) ----------

def render_swimlane_table(db, gate_obj: Dict[str, Any], CONFIG: Dict[str, Any]):
    pid = st.session_state.get("open_project")
    if not pid:
        st.info("Select a project above.")
        return

    proj = db.get_project(pid)
    role = st.session_state.get("role", "")

    # Active gate state only
    gate_state = proj.get("gates", {}).get(gate_obj["gate_id"], {})
    cp_map = gate_state.get("checkpoints", {})

    # Overall gate status (override-aware)
    decisions = [cp_map.get(cp["artifact_key"], {}).get("decision", "Pending") for cp in gate_obj["checkpoints"]]
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

    # Table header
    cols = st.columns([3, 3, 2, 2, 3])
    cols[0].markdown("**Checkpoint**")
    cols[1].markdown("**Artifact**")
    cols[2].markdown("**Submitted By**")
    cols[3].markdown("**Reviewed By**")
    cols[4].markdown("**Decision / AI**")

    # Rows
    for cp in gate_obj["checkpoints"]:
        row = st.columns([3, 3, 2, 2, 3])

        # 0) Checkpoint (plain text, NOT clickable) — from Excel "Checkpoint"
        row[0].write(cp.get("checkpoint", "—"))

        # 1) Artifact (clickable) — from Excel "Artifacts Produced"
        if row[1].button(
            cp["artifact"],
            key=f"art_{gate_obj['gate_id']}_{cp['artifact_key']}",
            help="Open artifact details",
        ):
            st.session_state[_artifact_modal_key(gate_obj["gate_id"], cp["artifact_key"])] = True

        # 2) Roles
        row[2].write(cp.get("submitted_by_role", ""))
        row[3].write(cp.get("reviewed_by_role", ""))

        # ------- Decision + AI (ALWAYS create these two columns first) -------
        dec_col, ai_col = row[4].columns([1, 1])

        # Current decision and reviewer/override flags
        cur_decision = cp_map.get(cp["artifact_key"], {}).get("decision", "Pending")
        reviewer_only = is_reviewer_for(cp, role)
        override_active = gate_state.get("overridden", False)
        override_value = gate_state.get("gate_status", "Pending") if override_active else None
        effective_decision = override_value if override_active else cur_decision

        # Decision dropdown (non-empty label; visually collapsed)
        with dec_col:
            new_decision = st.selectbox(
                "Decision",
                DECISIONS,
                index=DECISIONS.index(effective_decision) if effective_decision in DECISIONS else DECISIONS.index("Pending"),
                key=f"dec_{gate_obj['gate_id']}_{cp['artifact_key']}",
                disabled=True if override_active else not reviewer_only,
                label_visibility="collapsed",
            )

        # Precompute artifact payload presence for AI gating
        artifact_payload = cp_map.get(cp["artifact_key"], {}).get("payload", {}) or db.get_artifact_payload(pid, cp["artifact_key"]) or {}
        has_artifact = bool(artifact_payload)

        # AI suggestion (locked if overridden)
        with ai_col:
            ai_click = st.button(
                "Get AI Suggestion",
                key=f"ai_{gate_obj['gate_id']}_{cp['artifact_key']}",
                disabled=(not reviewer_only) or override_active,
            )
            if ai_click:
                st.session_state[_ai_modal_key(gate_obj["gate_id"], cp["artifact_key"])] = True

        # Persist manual decision only if NOT overridden
        if reviewer_only and (not override_active) and new_decision != cur_decision:
            db.save_checkpoint_decision(
                pid,
                gate_obj["gate_id"],
                cp["artifact_key"],
                new_decision,
                st.session_state.get("auth_user", "unknown"),
            )
            st.rerun()

        # -------- Artifact "modal" (container emulation) --------
        if st.session_state.get(_artifact_modal_key(gate_obj["gate_id"], cp["artifact_key"])):
            st.markdown("---")
            st.markdown(f"### Artifact — {cp['artifact']}")
            # Prefill from current gate or shared payload across gates
            payload = artifact_payload
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

        # -------- AI Suggestion "modal" (container emulation, new look) --------
        if st.session_state.get(_ai_modal_key(gate_obj["gate_id"], cp["artifact_key"])):
            st.markdown("---")
            # Styled card
            st.markdown(
                """
                <div style="
                    border:1px solid #e3e6ea;padding:16px;border-radius:10px;
                    background:#041329;">
                    <h4 style="margin:0 0 8px 0;">AI Suggestion</h4>
                """,
                unsafe_allow_html=True,
            )

            from ai import recommend_for_checkpoint
            suggestion = recommend_for_checkpoint(
                proj, gate_obj, cp,
                has_artifact=has_artifact,
                payload=artifact_payload
            )
            st.code(suggestion, language="markdown")

            if not has_artifact:
                st.warning("No artifact data found. The assistant will not recommend **Approve** without evidence.")

            c1, c2 = st.columns(2)
            apply_click = c1.button("Apply Suggestion", key=f"apply_{gate_obj['gate_id']}_{cp['artifact_key']}")
            dismiss_click = c2.button("Dismiss", key=f"dismiss_{gate_obj['gate_id']}_{cp['artifact_key']}")
            if apply_click:
                # Parse decision safely; never approve without artifact
                parsed = (
                    "Approve" if ("Suggested decision:** Approve" in suggestion and has_artifact)
                    else "Reject" if "Suggested decision:** Reject" in suggestion
                    else "ReScope" if "Suggested decision:** ReScope" in suggestion
                    else "Pending"
                )
                if (parsed == "Approve") and (not has_artifact):
                    parsed = "Pending"
                db.save_checkpoint_decision(
                    pid,
                    gate_obj["gate_id"],
                    cp["artifact_key"],
                    parsed,
                    st.session_state.get("auth_user", "unknown"),
                )
                st.session_state[_ai_modal_key(gate_obj["gate_id"], cp["artifact_key"])] = False
                st.rerun()
            if dismiss_click:
                st.session_state[_ai_modal_key(gate_obj["gate_id"], cp["artifact_key"])] = False
                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)  # close styled card

    # ----- CAIO override for gate status (ACTIVE GATE ONLY) -----
    if st.session_state.get("role", "") == "ChiefAIOfficer":
        with st.expander("CAIO Override Gate Status"):
            choice = st.selectbox(
                "Set gate status",
                DECISIONS,
                index=DECISIONS.index(overall) if overall in DECISIONS else DECISIONS.index("Pending"),
            )
            reason = st.text_input("Reason for override")
            if st.button("Apply Override", type="primary"):
                user = st.session_state.get("auth_user", "unknown")
                # Save override for ACTIVE gate only
                db.save_gate_status(pid, gate_obj["gate_id"], choice, user, reason)
                # Apply same decision to ALL checkpoints in THIS gate only
                for cp in gate_obj["checkpoints"]:
                    db.save_checkpoint_decision(pid, gate_obj["gate_id"], cp["artifact_key"], choice, user)
                st.success("Gate status overridden and checkpoint decisions updated for this gate.")
                st.rerun()

# ---------- CXO Dashboard ----------

def render_cxo_dashboard(db):
    import pandas as pd
    st.subheader("CXO Dashboard")

    projects = db.list_projects()
    if not projects:
        st.info("No projects yet. Add a project to see the dashboard.")
        return

    total = len(projects)
    gate_status_counts = {"Approve": 0, "Reject": 0, "Pending": 0, "ReScope": 0}
    proj_status_counts = {"ONGOING": 0, "COMPLETED": 0, "PENDING": 0}

    latest_rows = []
    for p in projects:
        pst = (p.get("status", "ONGOING") or "ONGOING").upper()
        proj_status_counts[pst] = proj_status_counts.get(pst, 0) + 1

        gates = p.get("gates", {})
        latest_gid = None
        latest_ts = -1
        latest_status = "Pending"
        for gid, gs in gates.items():
            ts = 0
            for ev in gs.get("audit", []):
                ts = max(ts, ev.get("ts", 0))
            if ts > latest_ts:
                latest_ts = ts
                latest_gid = gid
                latest_status = gs.get("gate_status", "Pending")
            gate_status_counts[gs.get("gate_status", "Pending")] = gate_status_counts.get(gs.get("gate_status", "Pending"), 0) + 1

        latest_rows.append({
            "Project": p.get("name", ""),
            "Current Gate": p.get("current_gate_id", ""),
            "Latest Gate Touched": latest_gid or p.get("current_gate_id", ""),
            "Latest Gate Status": latest_status,
            "Owner": p.get("owner", "")
        })

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Projects", total)
    c2.metric("Gates Approved", gate_status_counts.get("Approve", 0))
    c3.metric("Gates Pending", gate_status_counts.get("Pending", 0))
    c4.metric("Gates Rejected", gate_status_counts.get("Reject", 0))

    st.divider()

    status_df = pd.DataFrame.from_dict(gate_status_counts, orient="index", columns=["count"]).sort_index()
    st.caption("Gate status distribution")
    st.bar_chart(status_df)

    st.divider()
    st.caption("Latest project activity")
    latest_df = pd.DataFrame(latest_rows)
    st.dataframe(latest_df, use_container_width=True, hide_index=True)

    proj_df = pd.DataFrame.from_dict(proj_status_counts, orient="index", columns=["count"]).sort_index()
    st.caption("Project status overview")
    st.bar_chart(proj_df)

# ---------- Add Project (minimal form) ----------

def render_add_project_form(db):
    import time as _t
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

# ---------- Help ----------

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
    st.markdown(
        """
1. **Login** with your username/password. Your role controls access.
2. Go to **Home** to view the swimlane. Choose a project from the dropdown.
3. Click an **Artifact** to open its editor. Add evidence/notes and save.
4. **Reviewer/CAIO**: use the **Decision** dropdown or **Get AI Suggestion**.
5. **Overall Gate Status** auto-updates; CAIO can **Override** the active gate.
6. **CXO Dashboard** shows KPIs and charts.
7. **Add Project** creates a new record.
8. **Settings (CAIO)** sets the OpenAPI key, model, and can **Clear Session**.
        """
    )

# ---------- Settings (CAIO-only) ----------

def render_settings_page(db):
    st.subheader("Settings")
    role = st.session_state.get("role", "")
    if not is_caio(role):
        st.error("Settings are restricted to the Chief AI Officer.")
        return

    st.markdown("Manage OpenAPI credentials used for AI recommendations.")
    current = db.get_settings()
    with st.form("settings_form", clear_on_submit=False):
        api_key = st.text_input(
            "OpenAPI Key",
            type="password",
            value="",
            help="Key is stored obfuscated locally (DB). Leave blank to keep current.",
        )
        model = st.text_input("Model (e.g., gpt-4o-mini)", value=current.get("openapi_model", "gpt-4o-mini"))
        c1, c2, c3 = st.columns(3)
        save = c1.form_submit_button("Save", type="primary")
        clear = c2.form_submit_button("Clear Key")
        clear_session = c3.form_submit_button("Clear Session")  # CAIO-only

    if save:
        db.save_openapi_key(api_key.strip(), model.strip() if model.strip() else None)
        st.success("Settings saved.")
        st.rerun()

    if clear:
        db.clear_openapi_key()
        st.success("API key cleared.")
        st.rerun()

    if clear_session:
        # Remove common session keys
        for k in ["auth_user", "role", "page", "open_project", "active_gate"]:
            if k in st.session_state:
                del st.session_state[k]
        # Clear any modal state keys
        for k in list(st.session_state.keys()):
            if k.startswith("artifact_modal_") or k.startswith("ai_modal_"):
                del st.session_state[k]
        st.success("Session cleared.")
        st.rerun()
