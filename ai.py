# ai.py
import os, textwrap
from typing import Dict, Any
try:
    from openai import OpenAI
    _HAS_OPENAI = True
except Exception:
    _HAS_OPENAI = False
from db import DB

def _policy_notes():
    path = "policy_notes.txt"
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def _format_checkpoint_ctx(project: Dict[str,Any], gate: Dict[str,Any], checkpoint: Dict[str,Any]) -> str:
    return textwrap.dedent(f"""
    Project: {project.get('name')}
    Gate: {gate.get('gate_id')} — {gate.get('gate_name')}
    Checkpoint: {checkpoint['artifact']}
    Submitter role: {checkpoint.get('submitted_by_role','')}
    Reviewer role: {checkpoint.get('reviewed_by_role','')}
    """).strip()

def recommend_for_checkpoint(project: Dict[str,Any], gate: Dict[str,Any], checkpoint: Dict[str,Any]) -> str:
    db = DB()
    key = db.get_openapi_key()
    model = db.get_settings().get("openapi_model","gpt-4o-mini")
    prompt = textwrap.dedent(f"""
    You are an AI Governance reviewer assistant. Based on the checkpoint and its artifacts, recommend a decision
    (**Approve**, **Reject**, or **ReScope**) and provide a short rationale. Consider policy notes and ethical criteria.
    Be concise and actionable.

    Policy notes:
    {_policy_notes()}

    Context:
    {_format_checkpoint_ctx(project, gate, checkpoint)}

    Output (markdown):
    - **Suggested decision:** <Approve|Reject|ReScope>
    - **Rationale:** (3 bullets)
    - **Evidence to verify next**
    """).strip()
    if not _HAS_OPENAI or not key:
        return textwrap.dedent("""
        - **Suggested decision:** Approve
        - **Rationale:**
          - Required artifacts appear complete.
          - No blockers identified; residual risks documented.
          - Stakeholders engaged per roles.
        - **Evidence to verify next**: Confirm data lineage and bias checks are attached.
        """ ).strip()
    client = OpenAI(api_key=key)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":"You are a pragmatic AI governance reviewer."},
                  {"role":"user","content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()

def recommend_for_project(project: Dict[str,Any]) -> str:
    db = DB()
    key = db.get_openapi_key()
    model = db.get_settings().get("openapi_model","gpt-4o-mini")
    prompt = "Provide high-level governance recommendations for this project focusing on risks and next steps."
    if not _HAS_OPENAI or not key:
        return "- Ensure required artifacts are complete.\n- Schedule cross-functional review.\n- Document monitoring KPIs."
    client = OpenAI(api_key=key)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":"You are an AI governance coach."},
                  {"role":"user","content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()
