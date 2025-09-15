# ai.py
import os, textwrap
from typing import Dict, Any, Optional

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
    Checkpoint: {checkpoint.get('artifact') or checkpoint.get('checkpoint')}
    Submitter role: {checkpoint.get('submitted_by_role','')}
    Reviewer role: {checkpoint.get('reviewed_by_role','')}
    """).strip()

def recommend_for_checkpoint(
    project: Dict[str,Any],
    gate: Dict[str,Any],
    checkpoint: Dict[str,Any],
    has_artifact: bool,
    payload: Optional[dict] = None
) -> str:
    """
    Return a markdown suggestion:
    - **Suggested decision:** <Approve|Reject|ReScope>
    - **Rationale:** (3 bullets)
    - **Evidence to verify next**

    Constraint: if has_artifact is False, do NOT suggest Approve.
    """
    db = DB()
    key = db.get_openapi_key()
    model = db.get_settings().get("openapi_model", "gpt-4o-mini")

    rules = ("If no artifact evidence is present, you must NOT recommend Approve. "
             "Prefer Reject or ReScope with rationale.")
    payload_txt = f"Artifact payload keys: {list(payload.keys())}" if payload else "No artifact payload."

    prompt = textwrap.dedent(f"""
    You are an AI Governance reviewer assistant. Based on the checkpoint and artifacts, recommend a decision
    (**Approve**, **Reject**, or **ReScope**) and provide a short rationale. Be concise and actionable.

    Policy notes:
    {_policy_notes()}

    Constraint:
    - {rules if not has_artifact else "Artifact is present; you may recommend any status as appropriate."}

    Context:
    {_format_checkpoint_ctx(project, gate, checkpoint)}
    - {payload_txt}

    Output (markdown):
    - **Suggested decision:** <Approve|Reject|ReScope>
    - **Rationale:** (3 bullets)
    - **Evidence to verify next**
    """).strip()

    # Offline stub honors the constraint
    if not _HAS_OPENAI or not key:
        if not has_artifact:
            return textwrap.dedent("""
            - **Suggested decision:** ReScope
            - **Rationale:**
              - Required artifact is missing; evidence not provided.
              - Risks cannot be validated against governance criteria.
              - Scope clarification or artifact creation is needed.
            - **Evidence to verify next**: Provide the missing artifact and traceability notes.
            """).strip()
        else:
            return textwrap.dedent("""
            - **Suggested decision:** Approve
            - **Rationale:**
              - Required artifacts appear complete.
              - Risks addressed and residual risks documented.
              - Stakeholders acknowledged per roles.
            - **Evidence to verify next**: Confirm data lineage and bias checks are attached.
            """).strip()

    client = OpenAI(api_key=key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a pragmatic AI governance reviewer."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    text = resp.choices[0].message.content.strip()

    # Safety clamp: if the model returned Approve without artifact, downshift to ReScope
    if (not has_artifact) and ("**Suggested decision:** Approve" in text):
        text = text.replace("**Suggested decision:** Approve", "**Suggested decision:** ReScope")

    return text

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
