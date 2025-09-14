# ai.py
import os
import json
import textwrap
from typing import List, Dict, Any

# Uses OpenAI-compatible API via environment variable OPENAI_API_KEY.
# You can swap to any OpenAPI-compatible LLM by changing the client code.
try:
    from openai import OpenAI
    _HAS_OPENAI = True
except Exception:
    _HAS_OPENAI = False

POLICY_NOTES_FILE = "policy_notes.txt"

def _load_policy_notes() -> str:
    if not os.path.exists(POLICY_NOTES_FILE):
        return ""
    with open(POLICY_NOTES_FILE, "r", encoding="utf-8") as f:
        return f.read()

def train_policy_notes(notes: str):
    with open(POLICY_NOTES_FILE, "w", encoding="utf-8") as f:
        f.write(notes.strip())

def _format_context(project: Dict[str, Any], artifacts: List[Dict[str, Any]]) -> str:
    gate_idx = project.get("current_gate_index", 0)
    ctx = [
        f"Project: {project.get('name')}",
        f"Description: {project.get('description','')}",
        f"Current gate index: {gate_idx}",
        f"Artifacts at this gate: {[a['name'] for a in artifacts]}",
        f"Status: {project.get('status','')}",
    ]
    return "\n".join(ctx)

def _build_prompt(project: Dict[str, Any], artifacts: List[Dict[str, Any]]) -> str:
    policy = _load_policy_notes()
    ctx = _format_context(project, artifacts)
    return textwrap.dedent(f"""
    You are an AI Governance Assistant. Provide **actionable** next steps that align with ethical AI principles.
    Consider fairness, privacy, safety, transparency, and accountability.
    If key artifacts are missing, recommend how to create them.

    Organizational policy notes (mutable by CAIO):
    {policy}

    Project context:
    {ctx}

    Output format (markdown):
    - Summary risk posture
    - Top 3 immediate actions (short, imperative)
    - Evidence to collect
    - Stakeholders to engage
    - Go / No-Go guidance for advancing this gate
    """).strip()

def recommend_next_steps(project: Dict[str, Any], artifacts: List[Dict[str, Any]]) -> str:
    prompt = _build_prompt(project, artifacts)
    if not _HAS_OPENAI or "OPENAI_API_KEY" not in os.environ:
        # Offline fallback
        return textwrap.dedent("""
        **Summary risk posture:** Amber — missing one or more required artifacts.
        **Top 3 immediate actions:**
        1) Complete any missing artifacts for this gate.
        2) Log residual risks in the Risk Register with owners and due dates.
        3) Schedule a cross‑functional review with Governance and Security.
        **Evidence to collect:** data lineage, consent proof, bias test results.
        **Stakeholders:** Data Privacy, Security, Domain SME, Product Owner.
        **Go/No‑Go:** No-Go until required artifacts are submitted and reviewed.
        """).strip()

    client = OpenAI()
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role":"system","content":"You are a pragmatic AI governance coach."},
                  {"role":"user","content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()
