# generate_config_from_excel.py
import json, re, sys
import pandas as pd

def norm(s: str) -> str:
    return (s or "").strip().lower()

def pick_col(cols, target):
    # exact match after normalize (case/space tolerant)
    nmap = {norm(c): c for c in cols}
    t = norm(target)
    if t in nmap:
        return nmap[t]
    # soft fallback: allow minor punctuation differences
    for k, v in nmap.items():
        if k.replace(" ", "") == t.replace(" ", ""):
            return v
    return None

def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")

def main(xlsx_path: str, out_path: str):
    xls = pd.ExcelFile(xlsx_path)
    sheets = xls.sheet_names

    # Roles & Decision Rules
    roles_sheet = next((s for s in sheets if norm(s).startswith("roles")), None)
    decision_sheet = next((s for s in sheets if "decision" in norm(s)), None)

    roles = []
    if roles_sheet:
        rdf = xls.parse(roles_sheet).fillna("")
        # try to find "Role" and a responsibilities/description column
        role_col = pick_col(rdf.columns, "Role")
        resp_col = None
        for cand in ["Responsibilities", "Responsibility", "Description", "Notes"]:
            resp_col = pick_col(rdf.columns, cand)
            if resp_col:
                break
        for _, r in rdf.iterrows():
            role = str(r.get(role_col, "")).strip() if role_col else ""
            if role:
                roles.append({
                    "role": role,
                    "permissions": str(r.get(resp_col, "")).strip() if resp_col else ""
                })

    decision_rules = {}
    if decision_sheet:
        ddf = xls.parse(decision_sheet).fillna("")
        decision_rules = {
            "columns": [str(c) for c in ddf.columns],
            "rows": ddf.astype(str).to_dict(orient="records")
        }

    # Gates: tabs like G#_Name
    gate_tabs = [s for s in sheets if re.match(r"^G\d+_", s.strip(), flags=re.I)]
    gates = []
    for tab in gate_tabs:
        df = xls.parse(tab).fillna("")
        cols = list(df.columns)

        # *** STRICT columns as requested ***
        checkpoint_col = pick_col(cols, "Checkpoint")
        produced_col   = pick_col(cols, "Artifacts Produced")

        if not produced_col or not checkpoint_col:
            raise ValueError(
                f"[{tab}] Missing required columns. "
                f"Found: {cols}. Need 'Checkpoint' and 'Artifacts Produced'."
            )

        submitter_col = pick_col(cols, "Submitted By")
        reviewer_col  = pick_col(cols, "Reviewed By")
        status_col    = pick_col(cols, "Status")  # optional

        cps = []
        seen = set()
        for _, row in df.iterrows():
            checkpoint_name = str(row.get(checkpoint_col, "")).strip()
            artifact_name   = str(row.get(produced_col, "")).strip()
            if not artifact_name and not checkpoint_name:
                continue  # skip blank

            # Use artifact as the key anchor (same artifact across gates == same key)
            key_source = artifact_name or checkpoint_name
            akey = slug(key_source)
            if (tab, akey) in seen:
                continue
            seen.add((tab, akey))

            cps.append({
                "checkpoint": checkpoint_name,                   # ← from "Checkpoint"
                "artifact": artifact_name,                       # ← from "Artifacts Produced"
                "artifact_key": akey,
                "submitted_by_role": str(row.get(submitter_col, "")).strip() if submitter_col else "",
                "reviewed_by_role":  str(row.get(reviewer_col,  "")).strip() if reviewer_col  else "",
                "initial_status":    str(row.get(status_col,    "")).strip() if status_col    else ""
            })

        gates.append({
            "gate_id": tab.split("_")[0],                       # e.g., "G0"
            "gate_name": tab.split("_", 1)[1] if "_" in tab else tab,
            "checkpoints": cps
        })

    # sort by G#
    def gkey(g):
        m = re.match(r"g(\d+)", g["gate_id"], flags=re.I)
        return int(m.group(1)) if m else 999
    gates.sort(key=gkey)

    out = {
        "source_excel": xlsx_path.split("/")[-1],
        "roles": roles,
        "decision_rules": decision_rules,
        "gates": gates,
        "column_mapping": {
            "checkpoint": "Checkpoint",
            "artifact": "Artifacts Produced",
            "submitted_by_role": "Submitted By",
            "reviewed_by_role": "Reviewed By",
            "initial_status": "Status"
        }
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {out_path} with {len(gates)} gates.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_config_from_excel.py <excel_path> <out_json>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
